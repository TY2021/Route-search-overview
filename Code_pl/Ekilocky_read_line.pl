#Module
package ekilocky_read;
#use warnings;
use strict;
use URI;
use LWP::Simple;
use LWP::UserAgent;
use HTML::TreeBuilder;
use HTML::TokeParser;
use Time::HiRes;
use Encode;
use DBI;

#Read function
our @EXPORT_OK = qw/Read_timetable/;

#Prototype declaraion
sub Read_timetable;

#Test do
Read_timetable(11203)

#Read time table function
#Argument 0:line_cd
sub Read_timetable {
    my $line_name; #Line name
    my $line_name_h; #Line name
    my $line_cd = $_[0]; #Line code string
    my $line_cd_URL = 'line_cd='; #URL line node
    my $fname0 = "../Out Rail Info/NodeEdge Cystoscape/stations_JR_pl_1.csv";
    my $fname1 = "../TimetableSQL/".$_[0].".sqlite3";

    my $lineURL = 'http://eki.locky.jp/site/list?pageid=station&'; #Line URL
    my $st_dr_URL = 'http://eki.locky.jp/site/list?pageid=tbl&code='; #Station direction time table URL
    my $station_direction_URL; #Station direction time table URL
    my $tag_pre_HTML; #Extract HTML between <pre> and </pre>
    my $timetable_next_page = "http://eki.locky.jp/site/list?pageid=station&line_cd=".$line_cd."&page=1"; #Next page of time table staton list
    my $timetable_next_page_href = "list?pageid=station&line_cd=".$line_cd."&page=1";
    my $ekilocky_line_cd; #Ekilocky station line code
    my $database_station_cd; #Ekilocky station code convert to database station code
    my $database_direction_station_cd; #Ekilocky direction station code conver to database station code
    my $database_station_name; #Database station name(ekilocky station)
    my $timetable_destination; #Time table variable(destination)
    my $j = 0; #Counter of station name insert
    my $time_table_line_number = 0; #Counter of line number of time table
    my $train_type_number = 0; #Train type counter
    my $day_number = 0; #Array counter
    my $timetable_day_number = 0; #Number of day of time table(counter)
    my $ekilocky_station_number = 0; #Direction of ekilocky station counter
    my $ekilocky_direction_URL_number = 0; #Counter
    my $time_table_hour_number = 0; #Number of time table hour
    my $timetable_html_line_number = 0; #Line number of time table HTML
    my $for_type_length; #Length of station name
    my $primary_key = 0; #Primary key
    my $next_page_flag = 0; #Next page existing flag
    my $brackets_flag = 0; #Brackets exsit in direction
    my $destination_flag = 0; #Wether destination is insert flag
    my $type_flag = 0; #Whether train type insert
    my $limited_express_flag = 0; #Limited express flag
    my $timetable_hash; #Time table hash of scalar

    my @data; #File read array
    my @station_name; #JR station name list
    my @ekilocky_station_list; #Ekilocky station list
    my @ekilocky_direction_URL_list; #HTML of line page
    my @ekilocky_station_cd_list; #Ekilocky station code list
    my @ekilocky_direction_list; #Direction of every station(list)
    my @no_line_break_HTML; #Station time table temporary array
    my @day_list; #Day of week list
    my @timetable_hash_list; #Time table hash list
    my @ekilocky_station_cd_to_station_database_station_cd; #Ekilocky station code temporary
    my @station_database_station_name; #Station name of database
    my @train_type; #Time table element of alphabet(1 character)

    my %timetable_train_type; #Time table variable(train type)  hash
    my %timetable_hour_element; #Station time table(departure hour minute)  hash
    my %timetable_weekday; #Time table hash(weekday)

    my $index_start; #Index function return value
    my $station_length; #Station character number

    #SQLiteDB connect
    my $dbh0 = DBI->connect("dbi:SQLite:dbname=../SQLite/Station_DB.sqlite3");
    my $sth0; #SQLite Read variable;
    my $dbh1 = DBI->connect("dbi:SQLite:dbname=../SQLite/".$fname1);
    my $sth1; #SQLite Read variable;
    my @row; #Display array

    #Extract HTML variable
    my $station_list_page_temp;
    my $station_list_page;
    my $station_time_table_temp;
    my $station_time_table;

    #UserAgent set
    my $ua = LWP::UserAgent->new;
    $ua->agent("Mozilla"); #Agent set
    $ua->timeout(10); #Timeout set

    #Set JR station name
    open (IN, $fname0) or die "$!";
    if(!$_[1]) {
	     open (OUT, ">$fname1") or die "$!";
	     close(OUT);
    }
    #File read(Every 1 row)
    while (<IN>) {
	#Indention code delete
	chomp ($_);

	#csv separation
	@data = split(/,/, $_);

	#Remove full-width and half-width
	for (my $i = 0; $i < @data; $i++) {
	    $data[$i] =~ s/(　| )+//g;
	}

	#csv station code extract
	$station_name[$j] = $data[2];

	$j++;
    }
    #File close
    close(IN);

    #Read station_name line_name line_cd pref_name pref_cd from stations_db line_db pref_db
    #Extract line_name
    $sth0 = $dbh0->prepare('select line_name,line_name_h from line_db where line_cd = ?');
    $sth0->execute($line_cd);
    @row = $sth0->fetchrow_array;
    ($line_name,$line_name_h) = ($row[0],$row[1]);
    @row = ();
HT
    #Join pref_cd line_cd and make URL
    $line_cd_URL = $line_cd_URL.$line_cd;
    $lineURL = $lineURL.$line_cd_URL;

    #Make station list HTML::TreeBuilder
    #If 2 page exsit, set 2 page url
    if($_[1]) {
       $lineURL = $_[1];
       print "line_URL = $lineURL\n";
    }
    $station_list_page_temp = get($lineURL);
    $station_list_page = HTML::TreeBuilder->new_from_content($station_list_page_temp);

    #Extract <td> from the line HTML
    #Separete direction and time table url <td>
    foreach my $tag ($station_list_page->find("td")) {
	if($tag->as_HTML('&<>') !~ /align/) {
	    if($tag->as_HTML('&<>') ne '<td></td>') {
		#Station list in ekilocky line HTML
		if(encode('UTF-8',$tag->as_HTML('&<>')) !~ m/<td>(?:\xEF\xBD[\xA1-\xBF]|\xEF\xBE[\x80-\x9F])|[\x20-\x7E]<\/td>/) {
		    if(encode('UTF-8',$tag->as_HTML('&<>')) =~ m/<td>(.*?)<\/td>/) {
			$ekilocky_station_list[$ekilocky_station_number] = $1;
			$ekilocky_station_number++;
		    }
		#Time table URL <td>
		}else{
		    $ekilocky_direction_URL_list[$ekilocky_direction_URL_number] = encode('UTF-8',$tag->as_HTML('&<>'));
		    $ekilocky_direction_URL_number++;
		}
	    }
	}
    }

    #Extract next page of time table list
    foreach my $tag ($station_list_page->find("a")) {
	my $href = $tag->attr('href');
	if($href eq $timetable_next_page_href) {
	    $next_page_flag = 1;
	    print "next_page_flag = $next_page_flag\n";
	}
    }

    #Ekiloxky
    #Extract ekilocky station code and direction URL
    for(my $i = 0; $i < $ekilocky_direction_URL_number; $i++) {
	while($ekilocky_direction_URL_list[$i] =~ m#<a href="list\?pageid=tbl&amp;code=(.*?)">(.*?)</a>#g) {
	    push @ekilocky_station_cd_list, $1;
	    push @ekilocky_direction_list, $2;
	}

	#Extract direction station
	for(my $j0 = 0; $j0 < @ekilocky_direction_list; $j0++) {
	    #Delete '方面' from direction name
	    if(index(decode('utf-8',$ekilocky_direction_list[$j0]),decode('utf-8','方面')) ne -1) {
		my $direction_kanji = index(decode('utf-8',$ekilocky_direction_list[$j0]),decode('utf-8','方面'));
		$ekilocky_direction_list[$j0] = encode('utf-8',substr(decode('utf-8',$ekilocky_direction_list[$j0]), 0, $direction_kanji));
	    }
	    #Delete 'TBL' from direction name
	    if(index(decode('utf-8',$ekilocky_direction_list[$j0]),decode('utf-8','.TBL')) ne -1) {
		my $tbl = index(decode('utf-8',$ekilocky_direction_list[$j0]),decode('utf-8','.TBL'));
		$ekilocky_direction_list[$j0] = encode('utf-8',substr(decode('utf-8',$ekilocky_direction_list[$j0]), 0, $tbl));
	    }
	    #Symbol search (for delete symbol from direction name)
	    print "ekilocky_direction_list[$j0] = ".decode('utf-8',$ekilocky_direction_list[$j0])."\n";
	    while($ekilocky_direction_list[$j0] =~ /[\x3a]|[\x8146]|[\x2d]|[\x20]|[\x5f]|[\x8151]|[\x28]/) {
		#Decode station name for index
		$ekilocky_direction_list[$j0] = decode('utf-8',$ekilocky_direction_list[$j0]);
		#Delete '･' or '・' from direction
		if($& =~ /[\xa5]|[\x8145]|[\xE383BB]/) {
		    my $midpoint = 0;
		    if($& =~ /[\xa5]/) {
			my $midpoint_half = decode('utf-8','･');
			$midpoint = index($ekilocky_direction_list[$j0],$midpoint_half);
			print "0\n";
		    }
		    if($& =~ /[\x8145]/) {
			my $midpoint_full = decode('utf-8','・');
			$midpoint = index($ekilocky_direction_list[$j0],$midpoint_full);
			print "1\n";
		    }
		    if($& =~ /[\xE383BB]/) {
			my $midpoint_full = decode('utf-8','・');
			$midpoint = index($ekilocky_direction_list[$j0],$midpoint_full);
			print "2\n";
		    }
		    $ekilocky_direction_list[$j0] = substr($ekilocky_direction_list[$j0], 0, $midpoint);
		}
		#Delete : from direction
		if($& =~ /[\x3A]|[\x8146]/) {
		    my $colon = 0;
		    my $difference = 0;
		    if($& =~ /[\x3A]/) {
			my $colon_half = decode('utf-8',':');
			$colon = index($ekilocky_direction_list[$j0],$colon_half);
			$difference = (length($ekilocky_direction_list[$j0]) - $colon);
			print "3\n";
		    }
		    if($& =~ /[\x8146]/) {
			my $colon_full = decode('utf-8',':');
			$colon = index($ekilocky_direction_list[$j0],$colon_full);
			$difference = (length($ekilocky_direction_list[$j0]) - $colon);
			print "4\n";
		    }
		    $ekilocky_direction_list[$j0] = substr($ekilocky_direction_list[$j0], $colon, $difference);
		}
		#Delete - from direction
		if($& =~ /[\x2D]/) {
		    my $hyphen = 0;
		    my $hyphen_half = decode('utf-8','-');
		    $hyphen = index($ekilocky_direction_list[$j0],$hyphen_half);
		    $ekilocky_direction_list[$j0] = substr($ekilocky_direction_list[$j0], 0, $hyphen);
		    print "5\n";
		}
		#Delete blank from direction
		if($& =~ /[\x20]/) {
		    my $blank = 0;
		    my $blank_half = decode('utf-8',' ');
		    $blank = index($ekilocky_direction_list[$j0], $blank_half);
		    $ekilocky_direction_list[$j0] = substr($ekilocky_direction_list[$j0], 0, $blank);
		    print "6\n";

		}
		#Delete '_' from direction
		if($& =~ /[\x5f]/) {
		    my $underbar = 0;
		    my $underbar_half = decode('utf-8','_');
		    $underbar = index($ekilocky_direction_list[$j0], $underbar_half);
		    $ekilocky_direction_list[$j0] = substr($ekilocky_direction_list[$j0], 0, $underbar);
		    print "7\n";
		}
		if($& =~ /[\x8151]/) {
		    my $underbar = 0;
		    my $underbar_full = decode('utf-8','＿');
		    $underbar = index($ekilocky_direction_list[$j0], $underbar_full);
		    $ekilocky_direction_list[$j0] = substr($ekilocky_direction_list[$j0], 0, $underbar);
		    print "8\n";
		}
		#'()' in the direction that direction exclude
		if($& =~ /[\x28]/) {
		    $brackets_flag = 1;
		    print "()\n";
		    last;
		}
		#Encode station name for print
		$ekilocky_direction_list[$j0] = encode('utf-8',$ekilocky_direction_list[$j0]);

	    }

	    #If ()(full) exist in the direction, later process is pass
	    if($brackets_flag eq 1) {
		$brackets_flag = 0;
		next;
	    }

	    #Marge ekilocky station code and timeURL
	    $station_direction_URL = $st_dr_URL.$ekilocky_station_cd_list[$j0];

	    #Make station time table HTML::TreeBuilder
	    $station_time_table_temp = get($station_direction_URL);
	    $station_time_table = HTML::TreeBuilder->new_from_content($station_time_table_temp);

	    print "Station time table URL = $station_direction_URL\n";

	    #Extract <pre> from station time table HTML
	    foreach my $tag ($station_time_table->find("pre")) {
		if($tag->as_HTML('&<>') =~ /overflow:scroll/) {
		    $tag_pre_HTML = encode('UTF-8',$tag->as_HTML('&<>'));
		}
	    }

	    #Delete tag from station time table HTML
	    $tag_pre_HTML =~ s/<.*?>//g;

	    #Ekilocky HTML insert array (time table data, array number)
	    @no_line_break_HTML = split(/\n/, $tag_pre_HTML);
	    $time_table_line_number = @no_line_break_HTML;
	    $time_table_line_number = $time_table_line_number + 2;

	    #Delete comment in the ekilocky HTML
	    for(my $j1 = 0; $j1 < $time_table_line_number; $j1++) {
		if(Encode::_utf8_off($no_line_break_HTML[$j1]) =~ /^#[a-zA-Z0-9]*?/) {
		    $no_line_break_HTML[$j1] = '';
		}
	    }

	    #Separate time table variable
	    for(my $j2 = 0; $j2 < $time_table_line_number; $j2++) {
		if(decode('utf-8',$no_line_break_HTML[$j2]) =~ /(^[a-zA-Z]):(.*?$)/) {
		    my $alpha = encode('utf-8',$1);
		    my $for_type = encode('utf-8',$2);
		    my $for_type_temp = $2;
		    $for_type_temp =~ s/[\s　]+//g;
		    $for_type = encode('utf-8',$for_type_temp);
		    #Delete ';' in the direction
		    if(index($for_type, ";") ne -1) {
			$index_start = index($for_type, ";");
			$for_type_length = length($for_type);
			$for_type = substr($for_type, 0, $index_start);
		    }
		    #Delete ~行 of 行
		    if(index($for_type, "行") > 2) {
			$index_start = index($for_type, "行");
			$for_type_length = length($for_type);
			$for_type = substr($for_type, 0, $index_start);
		    }
		    #Insert variable and destination or train type
		    $timetable_train_type{$alpha} = $for_type;

		    #Train type count
		    $train_type_number++;
		}
	    }

	    #Separate day of week in the ekilocky HTML
	    for(my $j3 = $train_type_number; $j3 < $time_table_line_number; $j3++) {
		if(decode('utf-8',$no_line_break_HTML[$j3]) =~ /\[.*?\]/) {
		    $day_list[$train_type_number] = $no_line_break_HTML[$j3];
		    $day_number++;
		}
		if($no_line_break_HTML[$j3] =~ /(^[0-9]*?):(.*?$)/) {
		    $timetable_hour_element{$1} = $2;
		    $timetable_html_line_number--;
		    $timetable_html_line_number = $time_table_hour_number;
		    $time_table_hour_number++;
		}
		if ($time_table_hour_number eq $timetable_html_line_number && $time_table_hour_number ne 0 && $timetable_html_line_number ne 0) {
		    $timetable_hour_element{day} = $day_list[$timetable_day_number];
		    $timetable_hash = {%timetable_hour_element};
		    push(@timetable_hash_list,$timetable_hash);
		    $time_table_hour_number = 0;
		    $timetable_html_line_number = 0;
		    $timetable_day_number++;
		}
		$timetable_html_line_number++;
	    }

	    #Extract station code of the ekilocky station and destination station
	    $sth0 = $dbh0->prepare('select station_cd from stations_db where station_name = ?');
	    $sth0->execute($ekilocky_station_list[$i]);
	    while(@row = $sth0->fetchrow_array) {
		push @ekilocky_station_cd_to_station_database_station_cd, $row[0];
	    }
	    for(my $j4 = 0; $j4 < @ekilocky_station_cd_to_station_database_station_cd; $j4++) {
		$sth0 = $dbh0->prepare('select line_cd from line_db where station_id1 = ? or station_id2 = ?');
		$sth0->execute($ekilocky_station_cd_to_station_database_station_cd[$j4],$ekilocky_station_cd_to_station_database_station_cd[$j4]);
		$ekilocky_line_cd = $sth0->fetchrow_array;
		if($line_cd eq $ekilocky_line_cd) {
		    $database_station_cd = $ekilocky_station_cd_to_station_database_station_cd[$j4];
		    last;
		}
	    }

	    #Initialize SQL array
	    @ekilocky_station_cd_to_station_database_station_cd = ();
	    @station_database_station_name = ();
	    @row = ();

	    #Extract direction station code
	    $sth0 = $dbh0->prepare('select station_cd from stations_db where station_name = ?');
	    $sth0->execute($ekilocky_direction_list[$j0]);
	    while(@row = $sth0->fetchrow_array) {
		push @ekilocky_station_cd_to_station_database_station_cd, $row[0];
	    }
	    for(my $j5 = 0; $j5 < @ekilocky_station_cd_to_station_database_station_cd; $j5++) {
		$sth0 = $dbh0->prepare('select line_cd from line_db where station_id1 = ? or station_id2 = ?');
		$sth0->execute($ekilocky_station_cd_to_station_database_station_cd[$j5],$ekilocky_station_cd_to_station_database_station_cd[$j5]);
		$ekilocky_line_cd = $sth0->fetchrow_array;
		if($line_cd eq $ekilocky_line_cd) {
		    $database_direction_station_cd = $ekilocky_station_cd_to_station_database_station_cd[$j5];
		    last;
		}
	    }

	    #Make station time table in SQLite
	    print "$ekilocky_station_list[$i] | $ekilocky_direction_list[$j0] | $database_station_cd | $database_direction_station_cd\n";
	    $dbh1->do('create table '.$ekilocky_station_list[$i].'_'.$ekilocky_direction_list[$j0].'_'.$database_station_cd.'_'.$database_direction_station_cd.'(primary_key integer unique, hour integer, minute integer, destination text, type1 text)');

	    #Insert time table to sqlite table
	    %timetable_weekday = %{$timetable_hash_list[0]};
	    #Extract departure, time destination, train type
	    foreach my $key(keys(%timetable_weekday)) {
		my $timetable_hour = $key;
		if($key =~ /^[0-9]+$/) {
		    while($timetable_weekday{$key} =~ /([a-zA-Z0-9]+)/g) {
			my $timetable_element = $1;
			my $timetable_min;
			if($timetable_element =~ /[0-9]+/) {
			    $timetable_min = $&;
			    $primary_key++;
			}
			if($timetable_element =~ /[a-zA-Z]+/) {
			    my $timetable_alphabet = $&;
			    while($timetable_alphabet =~ /([a-zA-Z])/g) {
				#Destination set
				for(my $j6 = 0; $j6 < @station_name; $j6++) {
				    if($timetable_train_type{$&} eq $station_name[$j6]) {
					$timetable_destination = $timetable_train_type{$&};
					$destination_flag = 1;
					last;
				    }
				}
				#Train type set
				if(index($timetable_train_type{$&},"普通") ne -1 || index($timetable_train_type{$&},"快速") ne -1 || index($timetable_train_type{$&},"ライナー") ne -1 || index($timetable_train_type{$&},"リレー") ne -1) {
				    $train_type[0] =  $timetable_train_type{$&};
				    $type_flag = 1;
				}
				if(index($timetable_train_type{$&},"特急") ne -1 || index($timetable_train_type{$&},"急行") ne -1) {
				    $limited_express_flag = 1;
				}
			    }
			    #Set local type if train type is nothing
			    if($limited_express_flag eq 0 && $type_flag eq 0) {
				$train_type[0] = "普通";
				$type_flag = 1;
			    }
			}

			#Set '' for SQLite
			$timetable_destination = "'".$timetable_destination."'";
			$train_type[0] = "'".$train_type[0]."'";
			#Conversion time 24〜26
			if($key eq 0) {
			    $timetable_hour = 24;
			}
			if($key eq 1) {
			    $timetable_hour = 25;
			}
			if($key eq 2) {
			    $timetable_hour = 26;
			}
			#Insert time table element
			if($type_flag eq 1 && $destination_flag eq 1) {
			    print "$primary_key ";
			    print "$timetable_hour:";
			    print "$timetable_min";
			    print "$timetable_destination";
			    print "$train_type[0]\n";
			    $dbh1->do('insert into '.$ekilocky_station_list[$i].'_'.$ekilocky_direction_list[$j0].'_'.$database_station_cd.'_'.$database_direction_station_cd.' values('.$primary_key.', '.$timetable_hour.', '.$timetable_min.', '.$timetable_destination.', '.$train_type[0].')');
			}
			#Initialize
			$destination_flag = 0;
			$type_flag = 0;
			$limited_express_flag = 0;
			@train_type = ();
		    }
		}
	    }

	    #Counter array initialize
	    $time_table_line_number = 0;
	    $train_type_number = 0;
	    $day_number = 0;
	    $timetable_day_number = 0;
	    $time_table_hour_number = 0;
	    $timetable_html_line_number = 0;
	    $primary_key = 0;
	    @ekilocky_station_cd_to_station_database_station_cd = ();
	    @row = ();
	    @no_line_break_HTML = ();
	    @timetable_hash_list = ();
	    %timetable_train_type = {};
	    %timetable_hour_element = {};
	}

	#Counter array initialize
	@ekilocky_station_cd_list = ();
	@ekilocky_direction_list = ();
    }

    #If page 2 exsist, read next page
    if($next_page_flag eq 1) {
	Read_timetable($line_cd,$timetable_next_page);
    }
}

=pod
Read_timetable(11342);
Read_timetable(11323);
Read_timetable(11301);
Read_timetable(11502);
Read_timetable(11503);
Read_timetable(11601);
Read_timetable(11602);
Read_timetable(11609);
Read_timetable(11610);
Read_timetable(11611);
Read_timetable(11902);
Read_timetable(11903);
=cut
