const CATEGORY_COLORS = {
    'ML': '#4f46e5',
    'Data': '#10b981',
    'Cloud': '#f59e0b',
    'LLM': '#ec4899',
    'Engineering': '#06b6d4',
    'MLOps': '#8b5cf6',
    'Other': '#6b7280'
};

let skillChart = null;
let salaryChart = null;
let simulation = null;
let tooltip = null;

document.addEventListener('DOMContentLoaded', function() {
    initTooltip();
    loadSkillGraph();
    loadSkillFrequencyChart();
    loadSalaryDistributionChart();
    loadIndustryFilters();
    setupEventListeners();
});

function initTooltip() {
    const existingTooltip = document.querySelector('.node-tooltip');
    if (existingTooltip) {
        existingTooltip.remove();
    }
    tooltip = d3.select('body')
        .append('div')
        .attr('class', 'node-tooltip')
        .style('opacity', 0);
}

function setupEventListeners() {
    document.getElementById('reset-graph').addEventListener('click', resetGraph);
    document.getElementById('skill-industry-filter').addEventListener('change', loadSkillFrequencyChart);
    document.getElementById('skill-experience-filter').addEventListener('change', loadSkillFrequencyChart);
    document.getElementById('salary-group-filter').addEventListener('change', loadSalaryDistributionChart);
}

async function loadIndustryFilters() {
    try {
        const response = await fetch('/api/industry-skills');
        const data = await response.json();
        const select = document.getElementById('skill-industry-filter');
        data.forEach(item => {
            const option = document.createElement('option');
            option.value = item.industry;
            option.textContent = item.industry;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading industries:', error);
    }
}

async function loadSkillGraph() {
    const container = document.getElementById('skill-graph');
    const width = container.clientWidth;
    const height = 500;

    container.innerHTML = '';

    if (simulation) {
        simulation.stop();
        simulation = null;
    }

    try {
        const response = await fetch('/api/skill-graph');
        const data = await response.json();

        if (!data.nodes || data.nodes.length === 0) {
            container.innerHTML = '<div class="d-flex align-items-center justify-content-center h-100 text-muted"><div class="text-center"><p>No skill data available</p><p class="small">Load sample data to see the skill graph</p></div></div>';
            return;
        }

        const svg = d3.select('#skill-graph')
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .style('max-height', '500px');

        const g = svg.append('g');

        const zoom = d3.zoom()
            .scaleExtent([0.3, 3])
            .on('zoom', (event) => g.attr('transform', event.transform));

        svg.call(zoom);

        const maxCount = Math.max(...data.nodes.map(n => n.count));
        const nodeScale = d3.scaleLinear()
            .domain([1, maxCount])
            .range([8, 28]);

        const maxWeight = data.links.length > 0 ? Math.max(...data.links.map(l => l.weight)) : 1;
        const linkScale = d3.scaleLinear()
            .domain([1, maxWeight])
            .range([1, 6]);

        const nodeMap = new Map(data.nodes.map(n => [n.id, n]));
        const links = data.links
            .filter(l => nodeMap.has(l.source) && nodeMap.has(l.target))
            .map(l => ({
                source: l.source,
                target: l.target,
                weight: l.weight
            }));

        simulation = d3.forceSimulation(data.nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(80))
            .force('charge', d3.forceManyBody().strength(-150))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(d => nodeScale(d.count) + 5));

        const link = g.append('g')
            .selectAll('line')
            .data(links)
            .join('line')
            .attr('stroke', '#cbd5e1')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', d => linkScale(d.weight));

        const node = g.append('g')
            .selectAll('circle')
            .data(data.nodes)
            .join('circle')
            .attr('r', d => nodeScale(d.count))
            .attr('fill', d => CATEGORY_COLORS[d.category] || CATEGORY_COLORS['Other'])
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .style('cursor', 'pointer')
            .call(drag(simulation));

        const labels = g.append('g')
            .selectAll('text')
            .data(data.nodes)
            .join('text')
            .text(d => d.name)
            .attr('font-size', d => Math.max(10, nodeScale(d.count) / 2))
            .attr('dx', d => nodeScale(d.count) + 4)
            .attr('dy', 4)
            .attr('fill', '#374151')
            .style('pointer-events', 'none');

        node.on('mouseover', function(event, d) {
            d3.select(this)
                .transition()
                .duration(200)
                .attr('r', nodeScale(d.count) * 1.3);

            tooltip.transition().duration(200).style('opacity', 1);
            tooltip.html(`
                <strong>${d.name}</strong><br>
                Category: ${d.category}<br>
                Jobs: ${d.count}
            `)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px');
        })
        .on('mouseout', function(event, d) {
            d3.select(this)
                .transition()
                .duration(200)
                .attr('r', nodeScale(d.count));

            tooltip.transition().duration(200).style('opacity', 0);
        })
        .on('click', function(event, d) {
            highlightConnections(d, data, node, link, labels);
        });

        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node
                .attr('cx', d => d.x)
                .attr('cy', d => d.y);

            labels
                .attr('x', d => d.x)
                .attr('y', d => d.y);
        });

        renderLegend();

    } catch (error) {
        console.error('Error loading skill graph:', error);
        container.innerHTML = '<div class="d-flex align-items-center justify-content-center h-100 text-muted">Error loading skill graph</div>';
    }
}

function highlightConnections(selectedNode, data, nodeSelection, linkSelection, labelSelection) {
    const connectedNodes = new Set([selectedNode.id]);
    
    data.links.forEach(l => {
        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;
        if (sourceId === selectedNode.id) connectedNodes.add(targetId);
        if (targetId === selectedNode.id) connectedNodes.add(sourceId);
    });

    nodeSelection
        .transition()
        .duration(300)
        .style('opacity', d => connectedNodes.has(d.id) ? 1 : 0.2);

    linkSelection
        .transition()
        .duration(300)
        .style('opacity', l => {
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;
            return sourceId === selectedNode.id || targetId === selectedNode.id ? 1 : 0.1;
        });

    labelSelection
        .transition()
        .duration(300)
        .style('opacity', d => connectedNodes.has(d.id) ? 1 : 0.2);
}

function resetGraph() {
    d3.selectAll('#skill-graph circle')
        .transition()
        .duration(300)
        .style('opacity', 1);

    d3.selectAll('#skill-graph line')
        .transition()
        .duration(300)
        .style('opacity', 0.6);

    d3.selectAll('#skill-graph text')
        .transition()
        .duration(300)
        .style('opacity', 1);

    if (simulation) {
        simulation.alpha(0.3).restart();
    }
}

function renderLegend() {
    const legendContainer = document.getElementById('graph-legend');
    legendContainer.innerHTML = '';

    Object.entries(CATEGORY_COLORS).forEach(([category, color]) => {
        if (category !== 'Other') {
            const item = document.createElement('div');
            item.className = 'legend-item';
            item.innerHTML = `
                <div class="legend-color" style="background-color: ${color}"></div>
                <span>${category}</span>
            `;
            legendContainer.appendChild(item);
        }
    });
}

function drag(simulation) {
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
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended);
}

async function loadSkillFrequencyChart() {
    const industry = document.getElementById('skill-industry-filter').value;
    const experience = document.getElementById('skill-experience-filter').value;

    try {
        const params = new URLSearchParams();
        if (industry) params.append('industry', industry);
        if (experience) params.append('experience', experience);

        const response = await fetch(`/api/skill-frequency?${params}`);
        const data = await response.json();

        const ctx = document.getElementById('skill-chart').getContext('2d');

        if (skillChart) {
            skillChart.destroy();
            skillChart = null;
        }

        skillChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Job Count',
                    data: data.data,
                    backgroundColor: '#4f46e5',
                    borderRadius: 4,
                    barThickness: 20
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.raw} jobs require this skill`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            color: '#e2e8f0'
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading skill frequency:', error);
    }
}

async function loadSalaryDistributionChart() {
    const groupBy = document.getElementById('salary-group-filter').value;

    try {
        const response = await fetch(`/api/salary-distribution?group_by=${groupBy}`);
        const data = await response.json();

        const ctx = document.getElementById('salary-chart').getContext('2d');

        if (salaryChart) {
            salaryChart.destroy();
            salaryChart = null;
        }

        const colors = [
            '#4f46e5', '#10b981', '#f59e0b', '#ec4899', '#06b6d4',
            '#8b5cf6', '#ef4444', '#14b8a6', '#f97316', '#6366f1'
        ];

        salaryChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.label),
                datasets: [{
                    label: 'Average Salary (USD)',
                    data: data.map(d => d.avg),
                    backgroundColor: colors.slice(0, data.length),
                    borderRadius: 6,
                    barThickness: 40
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const item = data[context.dataIndex];
                                return [
                                    `Average: $${item.avg.toLocaleString()}`,
                                    `Range: $${item.min.toLocaleString()} - $${item.max.toLocaleString()}`,
                                    `Jobs: ${item.count}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + (value / 1000) + 'k';
                            }
                        },
                        grid: {
                            color: '#e2e8f0'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading salary distribution:', error);
    }
}
