// cbStop.js
// Display Chris Bolton's stop/charge data
// ASSUMES beatStopChgSumm.json: beatName -> [ [stopTot, [stopFracRace]], [chgTot, [chgFracRace], [diffRace] ]
//         produced by parseCBStop.py
//
// @author rik@electronicArtifacts.com
// @date 160304

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
var color = d3.scale.linear()
                .domain([0, 1])
                .range(['beige','blue'])
                .nice();
var AllRace = ['asian', 'black', 'hispanic', 'white', 'other'];
var RaceWeight = [100, 100, 100, 100, 100];

queue()
    .defer(d3.json, "beats09.geojson")
    .defer(d3.json, "beatStopChgSumm.json") // beatName -> [ [stopTot, [stopFracRace]], [chgTot, [chgFracRace], [diffRace] ]
    .await(ready);

function ready(error, oakGeo,beatTbl) {
    if (error) throw error;
    // console.log(oakGeo,beatTbl);

    function initControls() {
        var iwgt = 1; // / AllRace.length;
    	for (var r in AllRace) {
            var rname = AllRace[r];
    		RaceWeight[r] = iwgt;
    		var slider = d3.select("#"+rname+"_Slider")[0][0];
    		slider.value = 100 * iwgt;
    	}
        refill();
    };

    function updateStat(s) {
        statType = s;

        if (statType==="2") {
            color = d3.scale.linear()
                            .domain([-1, 0, 1])
                            .range(['red','yellow','green'])
                            .nice();
        } else {
            color = d3.scale.linear()
                            .domain([0, 1])
                            .range(['beige','blue'])
                            .nice();
        }

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

        // // renormalize: updated weight is fixed, others share residual proportional to current values
        // var totOtherWgt = 0
        // for (var r in AllRace) {
        //     if (r==upr) {continue};
        //     totOtherWgt = totOtherWgt + RaceWeight[r]
        // }
        // // var norm = totWgt / AllRace.length;
        // var diff = prevWgt - wgt;
        // var normDiff = diff / (AllRace.length - 1);
        // var resid = 1. - wgt;
        // for (var r in AllRace) {
        //     if (r==upr) {continue};
        //
        //     var rname = AllRace[r];
    	// 	RaceWeight[r] = RaceWeight[r] / totOtherWgt * resid;
    	// 	var slider = d3.select("#"+rname+"_Slider")[0][0];
    	// 	slider.value = 100 * RaceWeight[r] ;
        // }
        console.log("update1: RaceWeight="+RaceWeight);

        refill();
	};

    function refill() {
        d3.selectAll("path")
              .attr("fill", function (d) {
                  if (d.properties.Name in beatTbl) {
                     var v=0;
                     for (var r in AllRace) {
                         var cnt;
                         if (statType==="2") {
                             cnt = beatTbl[d.properties.Name][2][r];

                        } else {
                             cnt = beatTbl[d.properties.Name][statType][1][r];
                        }
                        var w = RaceWeight[r]
                        v = v + cnt * w;
                     }
                     // console.log(d.properties.Name+" "+v+ " " +color(v));
                     return color(v);
                 } else {
                     // console.log(d.properties.Name+" no data");
                     return "#F8F8FF";  // ghostWhite
                 };
             }) // eo-attr
         } // eo refill()

     function relabel() {
         d3.selectAll("title")
             .text(function(d) {
                 if (!(d.properties.Name in beatTbl)) {
                     return d.properties.Name;
                 } else if (statType==="2") {
                     var totStop = beatTbl[d.properties.Name][0][0];
                     var totChg = beatTbl[d.properties.Name][1][0];
                     return "Beat "+d.properties.Name+": Stops="+totStop+" / Charges="+totChg;
                 } else {
                     var tot = beatTbl[d.properties.Name][statType][0];
                     var lbl = "Beat "+d.properties.Name+": " + (statType==="0" ? "Stops=" : "Charges=");
                    return lbl+tot ;
                }
            })}  // eo-relabel

    d3.selectAll("input[name=statTypeRadio]")
        .on("change", function() {
            statType = this.value;
            if (statType==="2") {
                color = d3.scale.linear()
                                .domain([-1, 0, 1])
                                .range(['red','yellow','green'])
                                .nice();
            } else {
                color = d3.scale.linear()
                                .domain([0, 1])
                                .range(['beige','blue'])
                                .nice();
            }

            legendLinear = d3.legend.color()
              .shapeWidth(30)
              .orient('horizontal')
              .scale(color);

            viz.select(".legendLinear")
                .call(legendLinear);

            relabel();
            refill();

        }); // eo statTypeRadio

    d3.select("#resetButton").on("click", function() {initControls();});

    // input events seem useful (vs. change)
    d3.select("#asian_Slider").on("input", function() {updateWgt(this.value,0);});
	d3.select("#black_Slider").on("input", function() {updateWgt(this.value,1);});
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
              if (d.properties.Name in beatTbl) {
                 var v=0;
                 for (var r in AllRace) {
                     var cnt;
                     if (statType==="2") {
                         cnt = beatTbl[d.properties.Name][2][r];

                    } else {
                         cnt = beatTbl[d.properties.Name][statType][1][r];
                    }
                    var w = RaceWeight[r]
                    v = v + cnt * w;
                 }
                 // console.log(d.properties.Name+" "+v+ " " +color(v));
     			 return color(v);
             } else {
                 // console.log(d.properties.Name+" no data");
                return "#F8F8FF"; } // ghostWhite
          }) // eo-fill

          .append("svg:title")
               .text(function(d) {
                   if (!(d.properties.Name in beatTbl)) {
                       return d.properties.Name;
                   } else if (statType==="2") {
                       var totStop = beatTbl[d.properties.Name][0][0];
                       var totChg = beatTbl[d.properties.Name][1][0];
                       return "Beat "+d.properties.Name+": Stops="+totStop+" / Charges="+totChg;
                   } else {
                       var tot = beatTbl[d.properties.Name][statType][0];
                       var lbl = "Beat "+d.properties.Name+": " + (statType==="0" ? "Stops=" : "Charges=");
                      return lbl+tot ;
                  }
              }); // eo-text


    viz.append("g")
      .attr("class", "legendLinear")
      .attr("transform", "translate(15,15)");

    var legendLinear = d3.legend.color()
      .shapeWidth(30)
      .orient('horizontal')
      .title("Fraction of beat's data")
      .scale(color);

    viz.select(".legendLinear")
      .call(legendLinear);

}   // eo-ready()
