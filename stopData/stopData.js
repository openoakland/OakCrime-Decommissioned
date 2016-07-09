// stopData.js
// Display complete 2015 stop data from Figuroa
// ASSUMES beatStopSumm.json: beatSummTbl: beatName -> encType -> encResult -> race -> freq
//         produced by stopData.py
//
// @author rik@electronicArtifacts.com
// @date 160621

// ASSUMES other libraries loaded in HTML
// <script src="//d3js.org/d3.v3.min.js" charset="utf-8"></script>
// <script src="http://d3js.org/queue.v1.min.js"></script>
// <script src="d3-legend.js" charset="utf-8"></script>

var width = 960,
    height = 1160;

var projection = d3.geo.albersUsa()
    .scale(1)
    .translate([0,0]);

var path = d3.geo.path().projection(projection);

var viz = d3.select("#viz") // #viz
    .append("svg")
    .attr("width", width)
    .attr("height", height);

var statType="0";
var encType="0";
var encResult="0";

var color = d3.scale.linear()
                .domain([0, 1])
                .range(['beige','blue'])
                .nice();
var AllRace = ['asian', 'aa', 'hispanic', 'white', 'other'];
var RaceWeight = new Array();

queue()
    .defer(d3.json, "beats09.geojson")
    .defer(d3.json, "beatStopSumm.json") //  beatName -> encType -> encResult -> [ ertot, erByRace]
    .await(ready);

function ready(error, oakGeo,beatTbl) {
    if (error) throw error;
    // console.log(oakGeo,beatTbl);

    function initControls() {
        var iwgt = 1. // / AllRace.length;
    	for (var r in AllRace) {
            var rname = AllRace[r];
    		RaceWeight[r] = iwgt;
    		var slider = d3.select("#"+rname+"_Slider")[0][0];
    		slider.value = 100 * iwgt;
    	}
        refill();
		relabel();
    };

    function updateStat(s) {
        statType = s;

        color = d3.scale.linear()
                  .domain([0, 1])
                  .range(['beige','blue'])
                  .nice();

        legendLinear = d3.legend.color()
          .shapeWidth(30)
          .orient("horizontal")
          .scale(color);

        refill();
    }

    function updateWgt(v,upr) {
		var prevWgt = RaceWeight[upr]
		// <input type="range" min="1" max="100" id="slider1">
		var sliderRange = 100;
		var wgt = v/100;

        var prevWgt = RaceWeight[upr];
        RaceWeight[upr] = wgt;
		console.log("update1: motiv="+upr+" v="+v+" "+prevWgt+" --> "+RaceWeight[upr]);

        // renormalize: updated weight is fixed, others share residual proportional to current values
        var totOtherWgt = 0
        for (var r in AllRace) {
            if (r==upr) {continue};
            totOtherWgt = totOtherWgt + RaceWeight[r]
        }
        // var norm = totWgt / AllRace.length;
        var diff = prevWgt - wgt;
        var normDiff = diff / (AllRace.length - 1);
        var resid = 1. - wgt;
        for (var r in AllRace) {
            if (r==upr) {continue};
        
            var rname = AllRace[r];
    		RaceWeight[r] = RaceWeight[r] / totOtherWgt * resid;
    		var slider = d3.select("#"+rname+"_Slider")[0][0];
    		slider.value = 100 * RaceWeight[r] ;
        }

        console.log("update1: RaceWeight="+RaceWeight);

        refill();
	};

    function refill() {
        d3.selectAll("path")
              .attr("fill", function (d) {
                  if (d.properties.Name in beatTbl  &&
					  encType in beatTbl[d.properties.Name] &&
					  encResult in beatTbl[d.properties.Name][encType]) {

					  var tot = 0;
					  for (var r in AllRace) {
						  if (r in beatTbl[d.properties.Name][encType][encResult]) {
							  var cnt = beatTbl[d.properties.Name][encType][encResult][r];
							  tot = tot + cnt;
						  }
						  // 2do: should renormalize when a race has zero cnt?
					  }
					  var v=0;
					  for (var r in AllRace) {
						  if (r in beatTbl[d.properties.Name][encType][encResult]) {
							  var cnt = beatTbl[d.properties.Name][encType][encResult][r];
							  var w = RaceWeight[r]
							  var frac = cnt / tot;
							  v = v + frac * w;
						  }
						  // 2do: should renormalize when a race has zero cnt?
					  }
                     console.log(d.properties.Name+" "+v+ " " +color(v));
                     return color(v);
                 } else {
                     console.log(d.properties.Name+" no data");
                     return "#F8F8FF";  // ghostWhite
                 };
             }) // eo-attr
         } // eo refill()

     function relabel() {
         d3.selectAll("title")
             .text(function(d) {
                 if (!(d.properties.Name in beatTbl)) {
                     return "No data for " + d.properties.Name + "?!";
                 } else {
					 var etLbl;
					 var erLbl;
					 switch(encType) {
					 case "0": etLbl= "Vehicle"; break;
					 case "1": etLbl= "Pedestrian"; break;
					 case "2": etLbl= "Other"; break;
					 }

					 switch(encResult) {
					 case "0": erLbl= "Non-Arrest"; break;
					 case "1": erLbl= "Arrest"; break;
					 } 					 
					 var n = 0
					 if ((encType in beatTbl[d.properties.Name]) &&
						 (encResult in beatTbl[d.properties.Name][encType]))  {
						 var tot = 0;
						 for (var r in AllRace) {
							 if (r in beatTbl[d.properties.Name][encType][encResult]) {
								 tot = tot + beatTbl[d.properties.Name][encType][encResult][r];
							 }
						 }
					 } else {
						 tot = 0;
					 }
                     return "Beat "+d.properties.Name + " " + etLbl + " " + erLbl + " total: " + tot;
                 } 
            })}  // eo-relabel

    d3.selectAll("input[name=encTypeRadio]")
        .on("change", function() {
            encType = this.value;
 			color = d3.scale.linear()
                                .domain([0, 1])
                                .range(['beige','blue'])
                                .nice();
            legendLinear = d3.legend.color()
              .shapeWidth(30)
              .orient('horizontal')
              .scale(color);

            viz.select(".legendLinear")
                .call(legendLinear);

            relabel();
            refill();

        }); // eo encTypeRadio

	    d3.selectAll("input[name=encResultRadio]")
        .on("change", function() {
            encResult = this.value;
 			color = d3.scale.linear()
                                .domain([0, 1])
                                .range(['beige','blue'])
                                .nice();
            legendLinear = d3.legend.color()
              .shapeWidth(30)
              .orient('horizontal')
              .scale(color);

            viz.select(".legendLinear")
                .call(legendLinear);

            relabel();
            refill();

        }); // eo encResultRadio

    d3.select("#resetButton").on("click", function() {initControls();});

    // input events seem useful (vs. change)
    d3.select("#asian_Slider").on("input", function() {updateWgt(this.value,0);});
	d3.select("#aa_Slider").on("input", function() {updateWgt(this.value,1);});
    d3.select("#hispanic_Slider").on("input", function() {updateWgt(this.value,2);});
    d3.select("#white_Slider").on("input", function() {updateWgt(this.value,3);});
    d3.select("#other_Slider").on("input", function() {updateWgt(this.value,4);});

    initControls();

    var allFeat = oakGeo.features;

    var bounds = path.bounds(oakGeo);
    var s = 0.95 / Math.max((bounds[1][0] - bounds[0][0]) / width, (bounds[1][1] - bounds[0][1]) / height);
    var t = [(width - s * (bounds[1][0] + bounds[0][0])) / 2, (height - s * (bounds[1][1] + bounds[0][1])) / 2];

    projection
     .scale(s)
     .translate(t);

    viz.append("g")
      .attr("class", "tracts")
        .selectAll("path")
        .data(allFeat)
        .enter().append("path")
          .attr("d", path)
          .attr("fill-opacity", 0.8)
          .attr("stroke", "#222")
          .attr("fill", function (d) {
              if (d.properties.Name in beatTbl &&
				  encType in beatTbl[d.properties.Name] &&
				  encResult in beatTbl[d.properties.Name][encType]) {
				  var tot = 0;
                  for (var r in AllRace) {
					  if (r in beatTbl[d.properties.Name][encType][encResult]) {
						  var cnt = beatTbl[d.properties.Name][encType][encResult][r];
						  tot = tot + cnt;
					  }
					  // 2do: should renormalize when a race has zero cnt?
				  }

                  var v=0;
                  for (var r in AllRace) {
					  if (r in beatTbl[d.properties.Name][encType][encResult]) {
						  var cnt = beatTbl[d.properties.Name][encType][encResult][r];
						  var w = RaceWeight[r]
						  var frac = cnt / tot;
						  v = v + frac * w;
					  }
					  // 2do: should renormalize when a race has zero cnt?
				  }
                 console.log(d.properties.Name+" "+v+ " " +color(v));
     			 return color(v);
             } else {
                 // console.log(d.properties.Name+" no data");
                return "#F8F8FF"; } // ghostWhite
          }) // eo-fill

          .append("svg:title")
               .text(function(d) {
                   if (!(d.properties.Name in beatTbl)) {
                       return d.properties.Name;
                   } else {
					   var etLbl;
					   var erLbl;
					   switch(encType) {
					   case "0": etLbl= "Vehicle"; break;
					   case "1": etLbl= "Pedestrian"; break;
					   case "2": etLbl= "Other"; break;
					   }

					   switch(encResult) {
					   case "0": erLbl= "Non-arrest"; break;
					   case "1": erLbl= "Arrest"; break;
					   } 					 
					   var tot = 0;
					   for (var r in AllRace) {
						   if (r in beatTbl[d.properties.Name][encType][encResult]) {
							   tot = tot + beatTbl[d.properties.Name][encType][encResult][r];
						   }
					   }
                       return "Beat "+d.properties.Name + " " + etLbl + " " + erLbl + " total: " + tot;
				   } 
              }); // eo-text


    viz.append("g")
      .attr("class", "legendLinear")
      .attr("transform", "translate(15,15)");

    var legendLinear = d3.legend.color()
      .shapeWidth(30)
      .orient('horizontal')
      .title("Fraction of stops in beat")
      .scale(color);

    viz.select(".legendLinear")
      .call(legendLinear);

}   // eo-ready()
