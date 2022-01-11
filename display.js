//https://observablehq.com/@mariliamarkus/force-directed-graph
function drawChart(container, data) {
    //const width = 2560;
    //const height = 1440;
    const width = 8532;
    const height = 4000;
    const links = data.links.map(d => Object.create(d));
    const nodes = data.nodes.map(d => Object.create(d));
    const nodeStrength = -7500;

    const forceNode = d3.forceManyBody();
    const forceLink = d3.forceLink(links).id(d => d.id);
    const scale = d3.scaleOrdinal(d3.schemeCategory10);
    const color = d => scale(d.group);

    //const color = d3.scaleOrdinal(nodeGroup(d), d3.schemeTableau10);
    const drag = simulation => {

        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }

        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }

        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }

        return d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended);
    }
    if (nodeStrength !== undefined) forceNode.strength(nodeStrength);
    // if (linkStrength !== undefined) forceLink.strength(linkStrength);

    const simulation = d3.forceSimulation(nodes)
        .force("link", forceLink)
        .force("charge", forceNode)
        .force("center", d3.forceCenter(width / 2, height / 2));

    const svg = d3.select(container).append('svg')
        .attr('width', width)
        .attr('height', height)

    const link = svg.append("g")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke-width", d => Math.sqrt(d.value));


    const node = svg.append("g")
        .attr("stroke", "#000")
        .attr("stroke-width", 1.5)
        .selectAll("circle")
        .data(nodes)
        .join("circle")
        .attr("r", function (d) {
            return Math.trunc(d.rank) * 0.7;
        })
        .attr("fill", color)
        .call(drag(simulation))
        .on("mouseenter", (evt, d) => {
            link
                .attr("display", "none")
                .filter(l => l.source.id === d.id || l.target.id === d.id)
                .attr("display", "block");
        })
        .on("mouseleave", evt => {
            link.attr("display", "block");
        });
    //https://observablehq.com/@john-guerra/force-directed-graph-with-link-highlighting

    node.append("title")
        .text(d => `ID: ${d.id}\nRank: ${d.rank / 1000}`);

    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);
    });
}

