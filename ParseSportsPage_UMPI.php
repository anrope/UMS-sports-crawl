<?php
## This is setup to parse the 

include ("dbinfo.php");

$db_link = mysql_connect('umainedb.mainelyapps.com', $db_user, $db_pass)
    or die('Error: Could not connect to host: ' . mysql_error());

mysql_select_db($db_name) or die ('Error: Could not select database');
$db_table = "SportsEvents_UMPI";

# This script is used to parse the sports information from the black bear
# sports webpage.
//$sportsArr = array("bsb");

// NOTE: Might have to remove golf, not sure if this will be able to parse that page
$sportsArr = array("bsb", "mbkb", "mgolf", "msoc", 
					"mskiing", "wbkb", "wskiing", "wsoc", "sball", "wvball");

$monthArr = array("BLANK", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec");

# This is a critical variable used to tell if the game is home or away
$HOMETEAMNAME = "Me.-Presque Isle";

$baseSportsURL = "http://owls.umpi.edu/";
$urlForm = "http://owls.umpi.edu/sports/%s/%s/schedule";
$rssURLForm = $urlForm . "?print=rss";

function GetNewEvents ()
{
	print "Getting New Events<br/>\n";
	global $sportsArr, $monthArr, $urlForm, $rssURLForm;

	// Create the array of year ranges for the database and sports URLs 
	// it scans for the ranges: (LastYear-CurrentYear) and (CurrentYear-NextYear)
	$curYear4 = date("Y");
	$lastYear4 = intval($curYear4) - 1;
	$curYear2 = intval(substr($curYear4, 2));
	$nextYear2 = intval(substr($curYear4, 2)) + 1;
	$firstRange = $lastYear4 . "-" . $curYear2;
	$secondRange = $curYear4 . "-" . $nextYear2;
	$yearRangesArr = array($firstRange, $secondRange);

	foreach($yearRangesArr as $yearRange){
		foreach($sportsArr as $sport){
			$url = sprintf($rssURLForm, $sport, $yearRange);
			$xml = simplexml_load_file($url);
			if(!$xml){
					echo "No Valid XML<br/>";
					continue;
			}
			
			//$item = $xml->channel->item[13];
			foreach($xml->channel->item as $item){
				$desc = $item->description;
				$pattern = '/[[:alpha:]]* on ([[:alpha:]]+) ([[:digit:]]+), ([[:digit:]]{4}) at ([[:digit:]]+):([[:digit:]]{2}) ([[:alpha:]]{2}): ([[:print:]]+) vs. ([^,]+)[[:print:]]*/';
				// Array ( [0] => Baseball on Mar 8, 2011 at 6:00 PM: Maine vs. Florida St., Final, 2-10 [1] => Mar [2] => 8 [3] => 2011 [4] => 6 [5] => 00 [6] => PM [7] => Maine [8] => Florida St. ) 
				// 1: Month
				// 2: Day of month
				// 3: Year
				// 4: Hour of day (12 hour time)
				// 5: Minutes
				// 6: AM/PM
				// 7: Team A
				// 8: Team B (Home Team)
				if(preg_match($pattern, $desc, $matches)){
			
					// Game date and time
					$monthSearch = array_search($matches[1], $monthArr);
					if(!strcmp($matches[6], "AM")){
						$hour = intval($matches[4]);
					}
					else if(strcmp($matches[4], "12")){
						// We want to add 12 to the PM times except for the 12:00 PM case
						$hour = 12 + intval($matches[4]);
					}
					else{
						$hour = intval($matches[4]);
					}
					
					$dateTimeStr = sprintf("%d-%02d-%02d %02d:%02d:%02d", intval($matches[3]), intval($monthSearch), intval($matches[2]), $hour, intval($matches[5]), intval("00"));
					
					// Home Flag
					if(!strcmp($matches[8], $HOMETEAMNAME)){
						$home = "1";
					}
					else{
						$home = "0";
					}
						
					// teamA
					$teamA = $matches[7];
	
					// teamB
					$teamB = $matches[8];
	
					// Modified Date
					$modifiedDateTime = date("Y-m-d H:i:s");
					
					// Insert into the database
					AddEventIfNotPresent($dateTimeStr, $home, NULL, NULL, $sport, $teamA, $teamB, $yearRange, $modifiedDateTime);
				}
				else{
					echo "Error: A match was not found <br/>";
				}
				
			} // foreach event/item
		} // foreach sport
	} // foreach yearRangesArr

	// TODO: remove this please
	print "\nAll Done!!!!! \n\n";
}

function AddEventIfNotPresent ($dt, $h, $rl, $r, $s, $ta, $tb, $yr, $mdt)
{
	global $db_table;

	$isPresent = IsEventPresent($dt, $s);

	if(!$isPresent){
		$cols = "dateTime, home, ";
		$vals = '"' . $dt . '",' . $h .', ';
		
		if($rl){
			$cols .= "recapLink, ";
			$vals .= '"' .$rl .'", ';
		}
		if($r){
			$cols .= "result, ";
			$vals .= '"' . $r. '", ';
		}
		$cols .= "sport, teamA, teamB, yearRange, modifiedDateTime";
		$vals .= '"' . $s . '", "' . $ta . '", "' . $tb . '", "' . $yr . '", "' . $mdt . '"';
		
		$insertQuery = "INSERT INTO $db_table ($cols) VALUES ($vals)";
		$result  = mysql_query($insertQuery) or die("Error: Insert Query Failed: " . mysql_error() . "\n<br/>");
	}
	else{
		$updateQuery = 'UPDATE ' . $db_table . ' SET home="' . $h . '", ';
		
		// Update the recap link and result if they are not empty otherwise they should remain NULL in the table
		if($rl){
			$updateQuery .= 'recapLink="' . $rl . '", ';
		}
		if($r){
			$updateQuery .=  'result="' . $r . '", ';
		}

		$updateQuery .= 'teamA="' . $ta .'", teamB="' . $tb . '", modifiedDateTime="' . $mdt . '" where sport="' . $s . '" AND dateTime="' . $dt . '"';
		$result = mysql_query($updateQuery) or die("Error: Update Query Failed: " . mysql_error() . "\n<br/>");
	}
}

function IsEventPresent($dateTime, $sport)
{
	global $db_table;
	$ret = FALSE;

	$checkQuery = "SELECT * FROM " . $db_table . " WHERE dateTime='$dateTime' AND sport='$sport'";
	$result  = mysql_query($checkQuery) or die("Error: Select Query failed: " . mysql_error() . "\n<br/>");

	$num = mysql_num_rows($result);
	if($num == 0){
		$ret = FALSE;
	}
	else{
		$ret = TRUE;
	}

	return $ret;
}

function GetResultsAndRecaps ($dStr)
{
	global $urlForm, $baseSportsURL, $db_table, $monthArr;

	print "Getting results<br/>\n";

	// If the date string argument is empty then use the current date
	if(!strcmp($dStr, "")){
		$todaysDT = date("Y-m-d");
	}
	else{
		$todaysDT = $dStr;
	}

	// Print the date and time that the script is run
	$runDate = date("Y-m-d G:i e");
	print "Looking for results for date: " . $todaysDT . "\n";	
	print "Running on date and time : " . $runDate . "\n";

	// Month abbreviations in the schedule have a period after them
	$dateComps = explode("-", $todaysDT);
	$monthNum = $dateComps[1];
	$todaysM = $monthArr[intval($monthNum)] . ".";
	$todaysD = ltrim($dateComps[2], "0");
	$todaysSchedDate = $todaysM . " " . $todaysD;
	$sportsAndYears = GetSportsAndYearRanges($todaysDT);

	print_r($sportsAndYears);
	foreach($sportsAndYears as $syr){
		$dom = new domDocument;
		$sportAndYearRange = explode(";", $syr);
		$sport = $sportAndYearRange[0];
		$yearRange = $sportAndYearRange[1];
		$url = sprintf($urlForm, $sport, $yearRange);
		
		// TODO: remove this line
		print "USing url: " . $url;
		// Get the HTML from the schedule webpage
		$urlHTML = file_get_contents($url);
		
		// Remove excess whitespace
		$urlHTML = preg_replace('/\s\s+/', ' ', $urlHTML);

		echo "HTML for page:\n" . $urlHTML . "\n";

		// Load the domDocument with the HTML string
		@$dom->loadHTML($urlHTML);

		$divs = $dom->getElementsByTagName('div');
		$lastDate = "";

		// Get the rows containing the sport and current date
		// used in the update queries
		$todaysGamesQ = 'SELECT dateTime, teamA, teamB FROM ' . $db_table . ' WHERE sport="' . $sport . '" AND dateTime LIKE "' . $todaysDT . '%"';
		$todaysGamesR  = mysql_query($todaysGamesQ) or die("Error: Selecting todays games Query failed: " . mysql_error() . "\n");

		foreach($divs as $div){
			$classNode = $div->attributes->getNamedItem('class');
			if(($classNode == NULL) || (!strstr($classNode->nodeValue, "item"))){
				continue;
			}
	
			$childDivs = $div->getElementsByTagName('div');
	
			$dataDiv = $childDivs->item(0);
			$moreDiv = $childDivs->item(5);
			$dataChildDivs = $dataDiv->getElementsByTagName('div');
			$links = $moreDiv->getElementsByTagName('a');	
	
#			TODO: Should really check to see if the time/status is equal to Cancelled or Postponed and update the result 
#			based on that so people know why there is no result after the date has passed		
			$date = $dataChildDivs->item(0)->nodeValue;
			$date = FixupWhitespace($date);
			if(strlen($date) > 3){
				// Not an empty date so assign this to the last date
				$lastDate = $date;
			}
			else{
				// Empty Date Found use the last date (double header)
				$date = $lastDate;
			}
			$opponent = FixupWhitespace($dataChildDivs->item(1)->nodeValue);
			$resultStr = FixupWhitespace($dataChildDivs->item(2)->nodeValue);
			$timeOrStatus = FixupWhitespace($dataChildDivs->item(3)->nodeValue);
	
			$recapLink = "";
	
			foreach($links as $link){
				$nodeVal = $link->nodeValue;
				if(!strcmp($nodeVal, "Recap")){
					// Found the recap link
					$recapHREF = $link->attributes->getNamedItem('href');
					$recapLink = $baseSportsURL . $recapHREF->nodeValue;
					print "Recap: " .$recapHREF->nodeValue . "\n";
				}
			}

			print "Event date: $date\n";
			if(!strcmp($date, $todaysSchedDate)){
				// Found Todays event, perform the update to update the recapLink and resultStr fields in the database

				// TODO: Remove This
				print "Found today's date performing the update\n";
				$updateVals = "";
				print "Recap link: " . $recapLink;
				// Update the recap link and result if they are not empty otherwise they should remain NULL in the table
				if($recapLink && (!empty($recapLink))){
					$updateVals .= 'recapLink="' . $recapLink . '"';
				}
				if($resultStr && (!empty($resultStr))){
					if(!empty($updateVals))
						$updateVals .= ', ';
					$updateVals .= 'result="' . $resultStr . '"';
				}

				// If the values being updated are empty then we don't want to even do the update
				if(!empty($updateVals)){
					$gameRow = mysql_fetch_assoc($todaysGamesR);
					
					// Modified Date
					$modifiedDateTime = date("Y-m-d H:i:s");

					$updateVals .= ', modifiedDateTime="' . $modifiedDateTime . '"';

					$updateQuery = 'UPDATE ' . $db_table . ' SET ' . $updateVals . ' where sport="' . $sport . '" AND dateTime="' . $gameRow['dateTime'] . '" AND teamA="' . $gameRow['teamA'] . '" AND teamB="' . $gameRow['teamB'] . '"';

					print "\nUpdating DB with Query:\n $updateQuery\n\n";
					$result = mysql_query($updateQuery) or die("Error: Update Query: " . $updateQuery ." Failed With Error: " . mysql_error() . "\n<br/>");
				}
				else{
					echo "Empty update so doing nothing\n";
				}
			}
		} //  each div in the retrieved page
	} // each sport and year range
}

function GetSportsAndYearRanges($dateTime)
{
	global $db_table;
	$ret = array();
	
	// TODO: Uncomment the below lines
	$query = 'SELECT sport, yearRange FROM ' . $db_table . ' WHERE dateTime LIKE "' . $dateTime . '%"';
	$result  = mysql_query($query) or die("Error: Query failed: " . mysql_error() . "\n");

	// Loop over all rows in the query result
	while( $line = mysql_fetch_assoc($result) ){
		array_push($ret, $line['sport'] . ";" . $line['yearRange']);
	}
	
	return $ret;
}

function FixupWhitespace($str)
{
	return trim(preg_replace('/\s\s+/', ' ', $str));
}

function GetPreviousResults()
{
	global $db_table;

	$prevResultsQ = 'SELECT dateTime FROM ' . $db_table;
	echo "prevResultsQ: " . $prevResultsQ . "\n";
	$prevResultsR  = mysql_query($prevResultsQ) or die("Error: Query failed: " . mysql_error() . "\n");

	// Loop over all rows in the query result
	while( $line = mysql_fetch_assoc($prevResultsR) ){
		$DT = explode(" ", $line['dateTime']);
		echo "Getting Results for date=" . $DT[0] . "\n";
		GetResultsAndRecaps($DT[0]);
	}

}

## Main Program

if($argc < 2){
	echo "Incorrent number of args\n";
	return;
}

if(!strcmp($argv[1], "getevents")){
	// This should be run once or twice a week
	GetNewEvents();
}
else if(!strcmp($argv[1], "getresults")){
	// This should be run every 30 minutes or so
	GetResultsAndRecaps("");
}
else if(!strcmp($argv[1], "getpreviousresults")){
	// This is only run on a need-to-run basis
	GetPreviousResults();
}
?>
