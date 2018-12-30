package ripeatlasanalysis

import play.api.libs.json._

import java.io.BufferedWriter;
import java.io.FileWriter;
import org.apache.spark.sql.SparkSession
import java.util.{ Calendar, Date }
import java.util.Date
import java.text.SimpleDateFormat

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
object testJsone {

  def main(args: Array[String]): Unit = {

    // val userLists = Seq(User("hayat 1", 20, 67), User("bellafkih 2", 42, 90))
    val conf = new SparkConf().setAppName("RTT delays analysis").setMaster("local")

    import play.api.libs.functional.syntax._
    case class Location(lat: Double, long: Double)
    case class Resident(name: String, age: Int, role: Option[String])
    case class Place(name: String, location: Location, residents: Seq[Resident])
    implicit val locationWrites: Writes[Location] = (
      (JsPath \ "lat").write[Double] and
      (JsPath \ "long").write[Double])(unlift(Location.unapply))

    implicit val residentWrites: Writes[Resident] = (
      (JsPath \ "name").write[String] and
      (JsPath \ "age").write[Int] and
      (JsPath \ "role").writeNullable[String])(unlift(Resident.unapply))

    implicit val placeWrites: Writes[Place] = (
      (JsPath \ "name").write[String] and
      (JsPath \ "location").write[Location] and
      (JsPath \ "residents").write[Seq[Resident]])(unlift(Place.unapply))

    val place = Place(
      "Watership Down",
      Location(51.235685, -1.309197),
      Seq(
        Resident("Fiver", 4, None),
        Resident("Bigwig", 6, Some("Owsla"))))

    val json = Json.toJson(place)
    
    println(json)

    println("hello world")
  }
}