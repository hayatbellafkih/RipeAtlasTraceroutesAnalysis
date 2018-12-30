package javatools;

import java.util.regex.Pattern;

public class Tools {

	public static final String privatesOne = "^127\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$";
	public static final String privatesTwo = "^10\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$";
	public static final String privatesThree = "^192\\.168\\.\\d{1,3}.\\d{1,3}$";
	public static final String privatesFor = "^172.(1[6-9]|2[0-9]|3[0-1]).[0-9]{1,3}.[0-9]{1,3}$";

	public static Boolean isPrivateIp(String ip) {

		Boolean matched = false;
		Pattern patternOne = Pattern.compile(privatesOne);
		Pattern patternTwo = Pattern.compile(privatesTwo);
		Pattern patternThree = Pattern.compile(privatesThree);
		Pattern patternFor = Pattern.compile(privatesFor);
		

		
		if (patternOne.matcher(ip).find() || patternTwo.matcher(ip).find() || patternThree.matcher(ip).find() || patternFor.matcher(ip).find()) {
			matched = true;
		}

		return matched;
	}


}
