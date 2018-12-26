
import org.apache.spark.sql.SparkSession
import java.util.{ Calendar, Date }
import java.util.Date
import java.text.SimpleDateFormat
import org.joda.time.{ DateTime, Period, DateTimeZone, LocalDateTime }
import org.joda.time.format.{ DateTimeFormatter, DateTimeFormat }
import org.apache.spark.sql.functions.unix_timestamp
import org.apache.spark.SparkContext
import java.time.ZonedDateTime
import org.apache.spark.SparkConf
import org.apache.spark.sql.catalyst.ScalaReflection
import org.apache.spark.sql.types.StructType
import org.apache.spark.SparkConf
import java.sql.Timestamp;
import org.apache.spark.sql.Encoders
import java.lang.Integer
import java.io._

import org.apache.commons.math3.stat.interval.WilsonScoreInterval
import org.apache.commons.math3.stat.interval.ConfidenceInterval
import play.api.libs.json._
object AnalyseTraceroutes {

  //SHARED VARIABLES
  // the reference state of a link
  var reference = LinkState(Seq(), Seq(), Seq(), Seq())

  // the current state of a link
  var current = LinkState(Seq(), Seq(), Seq(), Seq())

  //Store the detected alarms
  var alarms: Seq[Int] = Seq()

  //Store the evolution of each link
  var linksEvolution: Seq[JsObject] = Seq()

  //CASE CLASS
  case class Hop(
    var result: Seq[Signal],
    hop:        Int)

  case class Signal(
    rtt:  Option[Double],
    x:    Option[String],
    from: Option[String])

  case class Traceroute(
    dst_name:  String,
    from:      String,
    prb_id:    BigInt,
    msm_id:    BigInt,
    timestamp: BigInt,
    result:    Seq[Hop])

  case class PreparedSignal(
    medianRtt: Double,
    from:      String)
  case class PreparedHop(
    var result: Seq[PreparedSignal],
    hop:        Int)
  case class MedianByHopTraceroute(
    dst_name:  String,
    from:      String,
    prb_id:    BigInt,
    msm_id:    BigInt,
    timestamp: BigInt,
    result:    Seq[PreparedHop])

  case class Link(
    ip1:     String,
    ip2:     String,
    rttDiff: Double)

  case class LinksTraceroute(
    dst_name:  String,
    from:      String,
    prb_id:    BigInt,
    msm_id:    BigInt,
    timestamp: BigInt,
    links:     Seq[Link])

  case class LinkIPs(
    ip1: String,
    ip2: String)

  case class DiffRtt(
    rtt:      Double,
    var link: LinkIPs,
    probe:    BigInt)

  case class DiffRTTPeriod(
    link:      LinkIPs,
    probes:    Seq[BigInt],
    rtts:      Seq[Double],
    var dates: Seq[Int])

  case class TraceroutesPerPeriod(
    traceroutes: Seq[Traceroute],
    timeWindow:  Int)

  case class SampleDiffRTT(
    linksDetails: DiffRTTPeriod,
    period:       Date)

  case class LinkState(
    var valueMedian: Seq[Double],
    var valueHi:     Seq[Double],
    var valueLow:    Seq[Double],
    var valueMean:   Seq[Double])

  case class LinkEvolution(
    link:      LinkIPs,
    reference: LinkState,
    current:   LinkState,
    alarms:    Seq[Int])

  /**
   *
   * Check if the given Signal is valid by checking :
   *   the source IP address if is not private;
   *   the signal is valid (not contains the * )
   *   the rtt exists
   *   the rtt is not negative
   *
   * @param signal
   * @return
   */
  def checkSignal(signal: Signal): Boolean = {
    if (signal.x == "*")
      return false
    else if (signal.rtt == None)
      return false
    else if (signal.rtt.get <= 0) {
      return false
    } else if (javatools.Tools.isPrivateIp(signal.from.get))
      return false
    else {
      return true
    }
  }

  /**
   *  Check a Traceroute by checking each Signal of each Hop  of the given Traceroute  object
   *
   *  @return Traceroute
   */
  def removeNegative(traceroute: Traceroute): Traceroute = {

    val outerList = traceroute.result
    for (temp <- outerList) {

      val hops = temp.result
      val newinnerList = hops.filter(checkSignal(_))
      temp.result = newinnerList

    }
    traceroute
  }

  /**
   * Calculate the median of the given sequence of doubles
   * @param seq  sequence of doubles
   * @return the calculated median
   */
  def medianCalculator(seq: Seq[Double]): Double = {
    val sortedSeq = seq.sortWith(_ < _)

    if (seq.size % 2 == 1) sortedSeq(sortedSeq.size / 2)
    else {
      val (up, down) = sortedSeq.splitAt(seq.size / 2)
      (up.last + down.head) / 2
    }
  }

  /**
   *
   * Retrieve the RTTs by given signals
   *
   * @param signals the signals, by one hop, having the same IP address
   *
   * @return the sequence of RTT of each signal
   */
  def getRtts(signals: Seq[Signal]): Seq[Double] = {
    val t = signals.map(f => f.rtt.get)
    return t
  }

  /**
   * Proceed a given Hop by grouping the signal by IP address
   *
   * @param hop Hop instance
   *
   * @return ProceedResult
   */
  def findMedianFromSignals(hop: Hop): PreparedHop = {

    val signals = hop.result
    val a = signals.groupBy(_.from.get)
    val c = a map { case (from, signaux) => from -> (getRtts(signaux)) }

    val b = c.map(f => PreparedSignal(medianCalculator(f._2), f._1))

    val d = b.toSeq
    return PreparedHop(d, hop.hop)

  }

  /**
   * Calculate the median by signal IP address
   */
  def computeMedianRTTByhop(traceroute: Traceroute): MedianByHopTraceroute = {
    val hops = traceroute.result
    val procHops = hops.map(f => findMedianFromSignals(f))

    MedianByHopTraceroute(traceroute.dst_name, traceroute.from, traceroute.prb_id, traceroute.msm_id, traceroute.timestamp, procHops)
  }

  /**
   * Find the link (s) between consecutives routers
   */
  def findAllLinks(firstRouter: PreparedHop, nextRouter: PreparedHop): Seq[Link] = {
    var links = Seq[Link]()

    for (currentRouter <- firstRouter.result) {
      for (prochainouter <- nextRouter.result) {
        links = links :+ Link(currentRouter.from, prochainouter.from, (currentRouter.medianRtt - prochainouter.medianRtt))
      }
    }
    // println(links.toString())
    return links
  }

  /**
   * Find all links for a given traceroute
   */
  def findLinksByTraceroute(spark: SparkSession, traceroute: MedianByHopTraceroute): LinksTraceroute = {
    val hops = traceroute.result
    val size = hops.size
    val s = hops.zipWithIndex
    val z = s.map {
      case (element, index) =>
        if (index + 1 < size) {
          findAllLinks(hops(index + 1), element)
        } else {
          null
        }
    }
    return new LinksTraceroute(traceroute.dst_name, traceroute.from, traceroute.prb_id, traceroute.msm_id, traceroute.timestamp, z.filter(p => p != null).flatten)
  }

  /**
   * Generate the timewindow start and end time
   */
  def generateDateSample(start: Int, end: Int, timewindow: Int): Seq[Int] = {
    Range(start, end, timewindow).toSeq
  }

  /**
   * Organize the links in a DiffRtt object
   */
  def resumeLinksTraceroute(traceroute: LinksTraceroute): Seq[DiffRtt] = {
    val links = traceroute.links
    val resumedLinks = links.map(f => DiffRtt(f.rttDiff, LinkIPs(f.ip1, f.ip2), traceroute.prb_id))
    resumedLinks
  }

  /**
   * Sort the links by sorting the two IPs address
   */
  def sortLinks(diffRtt: DiffRtt): DiffRtt = {

    val link = Seq(diffRtt.link.ip1, diffRtt.link.ip2)
    val sortedLink = link.sorted

    diffRtt.link = LinkIPs(sortedLink(0), sortedLink(1))

    diffRtt
  }

  /**
   * Get the traceroutes in the given timewindow
   */
  def getTraceroutes(spark: SparkSession, dataPath: String, startTimewindow: Int, endTimeWindow: Int): TraceroutesPerPeriod = {

    import spark.implicits._
    val rawtraceroutes = spark.read
      .schema(Encoders.product[Traceroute].schema)
      .json(dataPath)
      .as[Traceroute]

    println(rawtraceroutes.count())

    rawtraceroutes.toDF().show(100, truncate = false)
    val traceroutesPeriod = rawtraceroutes.filter(f => f.timestamp >= startTimewindow && f.timestamp < endTimeWindow)

    val f = traceroutesPeriod.collect().toSeq
    TraceroutesPerPeriod(f, startTimewindow)
  }

  //MAIN FUNCTION
  def main(args: Array[String]): Unit = {

    DateTimeZone.setDefault(DateTimeZone.UTC);
    val start = (new DateTime).withYear(2016)
      .withMonthOfYear(12)
      .withDayOfMonth(1)
      .withMinuteOfHour(0)
      .withHourOfDay(0)

    val end = (new DateTime).withYear(2016)
      .withMonthOfYear(12)
      .withDayOfMonth(25)
      .withMinuteOfHour(0)
      .withHourOfDay(0)

    val timewindow = 3600
    val timestamp = new Timestamp(start.getMillis()): Timestamp
    println("To timestam")
    println(timestamp)

    main(start, end)
  }

  def dafcha(spark: SparkSession, rawtraceroutes: TraceroutesPerPeriod): Seq[DiffRTTPeriod] = {
    println("Showing 10 rows of original Dataset")

    println("Filter failed traceroutes ... ")
    val notFailedTraceroutes = rawtraceroutes.traceroutes.filter(x => x.result(0).result != null)

    println("Remove invalid data  in hops")
    val cleanedTraceroutes = notFailedTraceroutes.map(x => removeNegative(x))

    println("Showing 10 rows of cleaned dataset ...")
    //cleanedTraceroutes. show(10, truncate = false)

    println("Calcul de la mediane par hop (la mediane par source du signal) ...")
    val tracerouteMedianByHop = cleanedTraceroutes.map(x => computeMedianRTTByhop(x))
    //tracerouteMedianByHop.show(10, truncate = false)

    println("Inference des liens par traceroute ...")
    import org.apache.spark.mllib.rdd.RDDFunctions._
    val tracerouteLinks = tracerouteMedianByHop.map(f => findLinksByTraceroute(spark, f))
    //println(tracerouteLinks.show(10, truncate = false))

    val rttDiff = tracerouteLinks.map(resumeLinksTraceroute)
    val fllaten = rttDiff.flatten

    // val finalresult = fllaten.show(100, truncate = false)

    val sorted = fllaten.map(f => sortLinks(f))
    // sorted.toSeq.toDF().show(100, truncate = false)

    val mergedData = sorted.groupBy(_.link)
    //println( mergedData.toString())

    val resumeData = mergedData.map(f => DiffRTTPeriod(f._1, f._2.map(_.probe), f._2.map(_.rtt), generateDatesSample(f._2.size, rawtraceroutes.timeWindow)))
    // resumeData.toSeq.toDF().show(100, truncate = false)

    println("Fin Inference des liens par traceroute ...")

    resumeData.toSeq
  }

  def findAlarms(spark: SparkSession, date: Int, reference: LinkState, dataPeriod: DiffRTTPeriod): Unit = {
    println("######################### Analysis for date" + date + " ######################")
    println("Find indices ...")
    val indices = dataPeriod.dates.zipWithIndex.filter(_._1 == date).map(_._2)

    println("Indices :" + indices.toString())
    val dist = indices.map(f => dataPeriod.rtts(f))

    println("MY DISTRIBUTION is " + dist.toString())

    println("Find RTTs for the current timewindow ...")
    val distSize = dist.size

    if (distSize > 0) {
      val wilsonCi = scoreWilsonScoreCalculator(spark, dist.size).map(f => f * dist.size)

      println("Before : current        " + current.toString())

      updateLinkCurrentState(spark, dist, current, wilsonCi)

      println("After : current         " + current.toString())

      println("Before reference " + reference.toString())

      val newDist = dist.sorted
      val tmpReference = reference

      if (tmpReference.valueMedian.size < 3) {
        println("tmpReference.valueMedian.size < 3 ")
        val newReferenceValueMedian = tmpReference.valueMedian :+ current.valueMedian.last
        val newReferenceValueHi = tmpReference.valueHi :+ newDist(javatools.JavaTools.getIntegerPart(wilsonCi(1)))
        println("oooooool  newDist(javatools.JavaTools.getIntegerPart(wilsonCi(1)) " + newDist(javatools.JavaTools.getIntegerPart(wilsonCi(1))))
        val newReferenceValueLow = tmpReference.valueLow :+ newDist(javatools.JavaTools.getIntegerPart(wilsonCi(0)))
        println("oooooool  newDist(javatools.JavaTools.getIntegerPart(wilsonCi(0)) " + newDist(javatools.JavaTools.getIntegerPart(wilsonCi(0))))

        reference.valueHi = newReferenceValueHi
        reference.valueLow = newReferenceValueLow
        reference.valueMedian = newReferenceValueMedian

      } else if (reference.valueMedian.size == 3) {

        println("reference.valueMedian.size == 3 ")

        val newReferenceValueMedian1 = tmpReference.valueMedian :+ medianCalculator(tmpReference.valueMedian)
        val newReferenceValueHi1 = tmpReference.valueHi :+ medianCalculator(tmpReference.valueHi)
        val newReferenceValueLow1 = tmpReference.valueLow :+ medianCalculator(tmpReference.valueLow)

        reference.valueHi = newReferenceValueHi1
        reference.valueLow = newReferenceValueLow1
        reference.valueMedian = newReferenceValueMedian1

        val newReferenceValueMedian = reference.valueMedian.map(f => reference.valueMedian.last)
        reference.valueMedian = newReferenceValueMedian
        val newReferenceValueHi = reference.valueHi.map(f => reference.valueHi.last)
        reference.valueHi = newReferenceValueHi

        val newReferenceValueLow = reference.valueLow.map(f => reference.valueLow.last)
        reference.valueLow = newReferenceValueLow
      } else {

        println("else ")
        val newReferenceValueMedian2 = tmpReference.valueMedian :+ (0.99 * tmpReference.valueMedian.last + 0.01 * current.valueMedian.last)
        val newReferenceValueHi2 = tmpReference.valueHi :+ (0.99 * tmpReference.valueHi.last + 0.01 * newDist(javatools.JavaTools.getIntegerPart(wilsonCi(1))))
        val newReferenceValueLow2 = tmpReference.valueLow :+ (0.99 * tmpReference.valueLow.last + 0.01 * newDist(javatools.JavaTools.getIntegerPart(wilsonCi(0))))
        reference.valueHi = newReferenceValueHi2
        reference.valueLow = newReferenceValueLow2
        reference.valueMedian = newReferenceValueMedian2
        if ((current.valueMedian.last - current.valueLow.last > reference.valueHi.last || current.valueMedian.last + current.valueHi.last < reference.valueLow.last) && scala.math.abs(current.valueMedian.last - reference.valueMedian.last) > 1) {
          //if (median[-1]-ciLow[-1] > smoothHi[-1] or median[-1]+ciHigh[-1] < smoothLow[-1]) and np.abs(median[-1]-smoothAvg[-1])
          println("BIG BIG")
          val updateAlarmsDates = alarms :+ date
          alarms = updateAlarmsDates

        }
      }
      println("After reference " + reference.toString())

    }
    println("ALARMS DATES  " + alarms)

  }

  def updateLinkCurrentState(spark: SparkSession, dist: Seq[Double], current: LinkState, wilsonCi: Seq[Double]) {
    val median = medianCalculator(dist)
    val newDist = dist.sorted

    println(current.toString())
    val tmp = current
    val newValueMedian = tmp.valueMedian :+ median
    current.valueMedian = newValueMedian

    val newValueLow = tmp.valueLow :+ (tmp.valueMedian.last - newDist(javatools.JavaTools.getIntegerPart(wilsonCi(0))))
    val newValueHi = tmp.valueHi :+ (newDist(javatools.JavaTools.getIntegerPart(wilsonCi(1)))) - current.valueMedian.last

    current.valueHi = newValueHi
    current.valueLow = newValueLow

    //println("Current state link")
    //println(current.toString())

  }

  def scoreWilsonScoreCalculator(spark: SparkSession, distSize: Int): Seq[Double] = {
    val sqlContext = spark.sqlContext
    val score = new WilsonScoreInterval().createInterval(distSize, distSize / 2, 0.95)
    Seq(score.getLowerBound, score.getUpperBound)
  }
  def generateDatesSample(size: Int, date: Int): Seq[Int] = {
    //val mydate=
    // val x = java.time.LocalDateTime.ofEpochSecond(date,0,java.time.ZoneOffset.UTC)
    List.tabulate(size)(n => date).toSeq

  }

  def convertUnixTimeStampToDate(timestamp: Int): java.time.LocalDateTime = {
    val x = java.time.LocalDateTime.ofEpochSecond(timestamp, 0, java.time.ZoneOffset.UTC)
    x
  }
  def updateDates() {

  }

  def outlierDetection(sampleDistributions: DiffRTTPeriod, smoothMean: Int, param: Int, expId: Int, ts: Int, probe2asn: Int, i2a: Int,
                       collection: Int, streaming: Int, probeip2asn: Int) {

  }

  def listAlarms(spark: SparkSession, rawDataLinkFiltred: DiffRTTPeriod, timewindow: Int, rangeDates: Seq[Int]) {

    print("Start listAlarms ...")
    //if (rawDataLinkFiltred.size != 0) {

    val rawDataLink = rawDataLinkFiltred
    println(rawDataLink.toString())
    val start = rawDataLink.dates.min
    val end = rawDataLink.dates.max + 86400

    val datesEvolution = start.to(end).by(timewindow)

    println("!!!!! rangeDates  !  " + rangeDates)
    println("!!!!! datesEvolution  !  " + datesEvolution)
    println(datesEvolution)

    //FIND ALARMS

    datesEvolution.foreach(f => findAlarms(spark, f, reference, rawDataLink))

    val linkEvolution = LinkEvolution(rawDataLink.link, reference, current, alarms)
    implicit val linkIPFormat = Json.format[LinkIPs]
    implicit val linkState = Json.format[LinkState]
    val user = Json.obj(
      "link" -> rawDataLink.link,
      "reference" -> linkEvolution.reference,
      "current" -> linkEvolution.current,
      "alarms" -> linkEvolution.alarms)

    val tmplinksEvolution = linksEvolution :+ user

    linksEvolution = tmplinksEvolution

    //println("!!!!!!!!!!!!!!!!!!!!!!!!!" + user)

    //user.toString()
    //System.exit(0)

    //}
  }

  def writeLine(writer: BufferedWriter, line: String) {
    writer.write(line)
    writer.newLine
  }
  def main(startTimeWindow: DateTime, endTimeWindow: DateTime): Unit = {
    implicit val localDateOrdering: Ordering[java.time.LocalDateTime] = Ordering.by(_.toEpochSecond(java.time.ZoneOffset.UTC))

    println("Préparation des traceroutes ...")

    //Create configuration
    val conf = new SparkConf().setAppName("RTT delays analysis").setMaster("local")

    //trouver le chemin vers les donnees
    val dataPath = getClass.getResource("/test/result.json").getPath

    //create spark session
    val spark = SparkSession
      .builder()
      .config(conf)
      .getOrCreate()
    import spark.implicits._

    //Chargement des traceroutes sur un case class

    val rangeDates = generateDateSample(1514768809, 1514791809, 3600)
    val timewindow = 3600
    val rangeDatesTimewindows = rangeDates.map(f => (f, f + timewindow))
    val traceroutesPerPeriod = rangeDatesTimewindows.map(f => getTraceroutes(spark, dataPath, f._1, f._2))

    //traceroutesPerPeriod.toDF().show(100, truncate = false)

    val dafchad = traceroutesPerPeriod.map(f => dafcha(spark, f))

    //dafchad.foreach(f => f.toDF().show(100, truncate = false))

    val collectedRTTDiff = dafchad.flatten
    //collectedRTTDiff.toDF().show(100, truncate = false)
    val finalResult = collectedRTTDiff.groupBy(_.link)
    val finalRawRttDiff = finalResult.map(f => DiffRTTPeriod(f._1, (f._2.map(_.probes)).flatten, (f._2.map(_.rtts)).flatten, (f._2.map(_.dates)).flatten))

    //finalRawRttDiff.toSeq.toDF().show(100, truncate = false)

    //val rawDataLinkFiltred = finalRawRttDiff.filter(p => p.link.ip1 == "185.147.12.31" && p.link.ip2 == "89.105.200.57").toSeq
    // val rawDataLinkFiltred = finalRawRttDiff.filter(p => p.link.ip1 == "185.147.12.19" && p.link.ip2 == "185.147.12.31").toSeq

    print("detcetion d'alarmes ...")

    finalRawRttDiff.toSeq.toDF().show()

    val rawDataLinkFiltred = finalRawRttDiff.map(p => listAlarms(spark, p, timewindow, rangeDates))

    val rddLinksEvolution = spark.sparkContext.parallelize(linksEvolution)

    val tmprddLinksEvolution = rddLinksEvolution.map(_.toString())
    
    tmprddLinksEvolution.saveAsTextFile("testSavingFile_0.json")
    val file = "testSavingFile_0.json"
    
//    val writer = new BufferedWriter(new FileWriter(file))
//    tmprddLinksEvolution.foreach(f => {
//      writer.write(f)
//      writer.newLine()
//    })

    //    rddLinksEvolution.map(writeLine(writer, _))
    //writer.close()

    //if (rawDataLinkFiltred.size != 0) {

    //      val rawDataLink = rawDataLinkFiltred(0)
    //      println(rawDataLink.toString())
    //
    //      val start = rawDataLink.dates.min
    //      val end = rawDataLink.dates.max + 86400
    //
    //      val datesEvolution = start.to(end).by(timewindow)
    //
    //      println("!!!!! rangeDates  !  " + rangeDates)
    //      println("!!!!! datesEvolution  !  " + datesEvolution)
    //      println(datesEvolution)
    //
    //      //FIND ALARMS
    //      datesEvolution.foreach(f => findAlarms(spark, f, reference, rawDataLink))
    //  }
  }
}