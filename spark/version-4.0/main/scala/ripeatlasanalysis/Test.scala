package ripeatlasanalysis
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
import play.api.libs.json._
object Test {
  def main(args: Array[String]) {
        val conf = new SparkConf().setAppName("RTT delays analysis").setMaster("local")

        //create spark session
val spark = SparkSession
   .builder()
   .appName("SparkSessionZipsExample")
   .config(conf)
   .getOrCreate()
    println("hello world")
  var linksEvolution: Seq[JsObject] = Seq(Json.obj(
      "link" ->2),Json.obj(
      "link" ->2),Json.obj(
      "link" ->2),Json.obj(
      "link" ->2),Json.obj(
      "link" ->2),Json.obj(
      "link" ->2),Json.obj(
      "link" ->2))
     val rddLinksEvolution = spark.sparkContext.parallelize(linksEvolution)
    
  }
}