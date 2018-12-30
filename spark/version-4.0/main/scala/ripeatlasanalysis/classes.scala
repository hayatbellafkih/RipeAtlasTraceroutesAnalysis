package ripeatlasanalysis

import java.util.Date

object classes {
  
  
  //CASE CLASS

  case class AlarmsDates(
    var dates: Seq[Int] = Seq())
  case class AlarmsValues(
    var medians: Seq[Double] = Seq())
    
  case class AllDates(
    var dates: Seq[Int] = Seq())
  case class Hop(
    var result: Seq[Signal],
    hop:        Int)



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
    timestamp: BigInt =0,
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
    
  case class TracerouteWithTimewindow(
      
      traceroute : Traceroute,
      period :  Int
      )
      

  case class LinkState(
    var valueMedian: Seq[Double],
    var valueHi:     Seq[Double],
    var valueLow:    Seq[Double],
    var valueMean:   Seq[Double])

  case class LinkEvolution(
    link:      LinkIPs,
    reference: LinkState,
    current:   LinkState,
    alarmsDates:    Seq[Int],
    alarmsValues:    Seq[Double],
    dates : Seq[Int])
    case class Signal(
    rtt:  Option[Double],
    x:    Option[String],
    from: Option[String])
    
    
}