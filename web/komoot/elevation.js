let svg = null;
let x = 0;
let y = 0;
let ymin = 0;
let ymax = 0;

function radians(d) {
    return d * (Math.PI / 180);
}

function distance(lat1, lon1, lat2, lon2) {
    let R = 6372800;

    let phi1 = radians(lat1);
    let phi2 = radians(lat2);
    let dphi = radians(lat2 - lat1);
    let dlambda = radians(lon2 - lon1);

    let a = Math.sin(dphi / 2) ** 2 + Math.cos(phi1) * Math.cos(phi2) * Math.sin(dlambda / 2) ** 2;

    return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function updateDistance(d) {
    // remove the old line
    d3.select("#currentPosition").remove();

    // draw the new line
    svg.append("line")
        .attr('id', 'currentPosition')
        .attr("x1", x(d))
        .attr("y1", y(ymin))
        .attr("x2", x(d))
        .attr("y2", y(ymax))
        .style("stroke-width", 2)
        .style("stroke", "orange")
        .style("fill", "none");
}

function updateElevation(path, highlights) {
    d3.select("#elevationGraph").remove();
    svg = d3.select("#elevation-outlet").append("svg")
        .attr("id", "elevationGraph")
        .attr("width", '100%')
        .attr("height", '100%')
        .attr('viewBox', '-30 -10 1240 160')
        .attr('preserveAspectRatio', 'xMinYMin')
        .append("g");

    // map in distances
    let dist = 0;
    let [ plat, plon, palt ] = [ null, null, null ];

    path = path.map(function(point) {
       let [ lat, lon, alt] = point;
       if ( plat === null ) {
           dist = 0;
       } else {
           dist = dist + distance(plat, plon, lat, lon);
       }
       point.push(dist);
       [ plat, plon, palt ] = point;

       return [dist/1000, alt];
    });

    // Add X axis
    x = d3.scaleLinear()
      .domain([0, d3.max(path, function(d) { return d[0]; })])
      .range([ 0, 1200 ]);

    svg.append("g")
      .attr("transform", "translate(0, 130)")
      .attr('class', 'elevationAxis')
      .call(d3.axisBottom(x));

    // Add Y axis
    ymin = d3.min(path, function(d) { return d[1]; });
    ymax = d3.max(path, function(d) { return d[1]; });
    y = d3.scaleLinear()
      .domain([ymin, ymax])
      .range([ 130, 0 ]);

    svg.append("g")
      .attr('class', 'elevationAxis')
      .call(d3.axisLeft(y));

    // Add the area
    svg.append("path")
      .datum(path)
      .attr("fill", "grey")
      .attr("stroke", "darkgrey")
      .attr("stroke-width", 1.5)
      .attr("d", d3.area()
        .x(function(d) { return x(d[0]) })
        .y0(y(ymin))
        .y1(function(d) { return y(d[1]) })
        )

    for (let hl in highlights) {
        // draw the new line
        svg.append("line")
            .attr("x1", x(highlights[hl]/1000))
            .attr("y1", y(ymin))
            .attr("x2", x(highlights[hl]/1000))
            .attr("y2", y(ymax))
            .style("stroke-width", 2)
            .style("stroke", "blue")
            .style("fill", "none");
    }
}