// State Variables
let parsedData = [];
let detectedM = 5; // Default bucket multiplier
let chartInstance = null;

// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const resBanner = document.getElementById('resolution-banner');
const resValue = document.getElementById('res-value');

// Slider & Input Elements
const paramTpmGsu = document.getElementById('param-tpm_gsu');
const paramGsuCost = document.getElementById('param-gsu_cost');
const paramInputRate = document.getElementById('param-input_rate');
const paramOutputRate = document.getElementById('param-output_rate');
const paramRatio = document.getElementById('param-ratio');
const paramPaygoMult = document.getElementById('param-paygo_mult');

const sliders = [paramTpmGsu, paramGsuCost, paramInputRate, paramOutputRate, paramRatio, paramPaygoMult];

// Event Listeners for file upload
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFileSelect);

// Auto-run test if requested via URL param (Local server required)
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.search.includes('test=true')) {
        fetch('my_sample_csv/sample_00.csv')
            .then(res => res.text())
            .then(csvText => {
                Papa.parse(csvText, {
                    header: true,
                    dynamicTyping: true,
                    complete: function(results) {
                        parsedData = results.data
                            .filter(row => row.time && !isNaN(new Date(row.time).getTime()))
                            .map(row => ({
                                time: new Date(row.time),
                                tpm: parseFloat(row.tpm) || 0
                            })).sort((a, b) => a.time - b.time);
                        detectResolution();
                        runSimulation();
                        renderChart();
                    }
                });
            });
    }
});


dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
        handleFileUpdate(e.dataTransfer.files[0]);
    }
});

// Update slider labels live
sliders.forEach(slider => {
    slider.addEventListener('input', (e) => {
        updateLabel(e.target.id);
    });
});

// Calculate Button Trigger
document.getElementById('calc-btn').addEventListener('click', () => {
    if (parsedData.length > 0) {
        runSimulation();
        renderChart();
    } else {
        alert("Please upload a CSV file first.");
    }
});

document.getElementById('reset-zoom').addEventListener('click', () => {
    if (chartInstance) {
        chartInstance.resetZoom();
        document.getElementById('reset-zoom').style.display = 'none';
    }
});


function updateLabel(id) {
    if (id === 'param-tpm_gsu') document.getElementById('val-tpm_gsu').innerText = Number(paramTpmGsu.value).toLocaleString();
    if (id === 'param-gsu_cost') document.getElementById('val-gsu_cost').innerText = `$${Number(paramGsuCost.value).toLocaleString()}`;
    if (id === 'param-input_rate') document.getElementById('val-input_rate').innerText = `$${parseFloat(paramInputRate.value).toFixed(2)}`;
    if (id === 'param-output_rate') document.getElementById('val-output_rate').innerText = `$${parseFloat(paramOutputRate.value).toFixed(2)}`;
    if (id === 'param-paygo_mult') document.getElementById('val-paygo_mult').innerText = `${parseFloat(paramPaygoMult.value).toFixed(1)}x`;
    if (id === 'param-ratio') {
        let inputP = paramRatio.value;
        let outputP = 100 - inputP;
        document.getElementById('val-ratio').innerText = `${inputP}/${outputP}`;
    }
}

function handleFileSelect(e) {
    if (e.target.files.length > 0) {
        handleFileUpdate(e.target.files[0]);
    }
}

function handleFileUpdate(file) {
    Papa.parse(file, {
        header: true,
        dynamicTyping: true,
        skipEmptyLines: true,
        complete: function(results) {
            if (results.data && results.data.length > 0 && 'tpm' in results.data[0]) {
                parsedData = results.data
                    .filter(row => row.time && !isNaN(new Date(row.time).getTime()))
                    .map(row => ({
                        time: new Date(row.time),
                        tpm: parseFloat(row.tpm) || 0
                    })).sort((a, b) => a.time - b.time);

                detectResolution();
                runSimulation();
                renderChart();
            } else {
                alert("Invalid CSV format. Ensure 'time' and 'tpm' headers are present.");
            }
        }
    });
}

function detectResolution() {
    if (parsedData.length < 2) return;
    
    // Average time difference in minutes
    let diffs = [];
    for (let i = 1; i < parsedData.length; i++) {
        let diff = (parsedData[i].time - parsedData[i-1].time) / (1000 * 60);
        if (diff > 0 && diff < 100) diffs.push(diff); // Filter out gaps/discontinuities
    }

    // Median diff
    diffs.sort((a,b)=>a-b);
    let medianDiff = diffs[Math.floor(diffs.length/2)] || 5;
    detectedM = Math.max(1, Math.round(medianDiff)); // Minimum 1 minute

    resBanner.style.display = 'block';
    resValue.innerText = `${detectedM} Minute${detectedM > 1 ? 's' : ''}`;
}

function runSimulation() {
    const tpmPerGsu = parseFloat(paramTpmGsu.value);
    const gsuCost = parseFloat(paramGsuCost.value);
    const inputRate = parseFloat(paramInputRate.value);
    const outputRate = parseFloat(paramOutputRate.value);
    const inputRatio = parseFloat(paramRatio.value) / 100;
    const outputRatio = 1 - inputRatio;
    const paygoMult = parseFloat(paramPaygoMult.value);

    // Pre-aggregations
    let totalTokens = parsedData.reduce((sum, row) => sum + row.tpm * detectedM, 0);
    let peakTpm = Math.max(...parsedData.map(row => row.tpm));

    document.getElementById('metric-total_tokens').innerText = (totalTokens / 1_000_000_000).toFixed(2) + " B";
    document.getElementById('metric-peak_tpm').innerText = (peakTpm / 1_000_000).toFixed(1) + " M";

    // Dynamic Sweep to find precise absolute optimal GSU
    let optimalCand = Math.ceil(peakTpm / tpmPerGsu);
    let minCost = Infinity;
    let minGsuRow = 1;
    let sweepCache = {};

    for (let gsu = 1; gsu <= optimalCand; gsu++) {
        let threshold = gsu * tpmPerGsu;
        let spilloverTotal = 0;
        let utilizeTotal = 0;

        parsedData.forEach(row => {
            spilloverTotal += Math.max(0, row.tpm - threshold) * detectedM;
            utilizeTotal += Math.min(row.tpm, threshold) * detectedM;
        });

        let ptCost = gsu * gsuCost;
        let totalAvailable = threshold * detectedM * parsedData.length;
        let utilRate = totalAvailable > 0 ? (utilizeTotal / totalAvailable) * 100 : 0;

        let spilledInput = spilloverTotal * inputRatio;
        let spilledOutput = spilloverTotal * outputRatio;
        let paygoCost = ((spilledInput / 1000000) * inputRate + (spilledOutput / 1000000) * outputRate) * paygoMult;
        let totalCombined = ptCost + paygoCost;

        sweepCache[gsu] = {
            threshold,
            ptCost,
            utilRate,
            spilloverB: spilloverTotal / 1_000_000_000,
            paygoCost,
            totalCombined
        };

        if (totalCombined < minCost) {
            minCost = totalCombined;
            minGsuRow = gsu;
        }
    }

    document.getElementById('metric-optimal_gsu').innerText = minGsuRow;
    document.getElementById('metric-total_cost').innerText = `$${Math.round(minCost).toLocaleString()}`;

    // Generate Display Candidates Grid surrounding exact optimum
    let gsuCandidates = [5, 10, 20, 24, 50, 100, 200];
    let offsets = [-15, -10, -5, 0, 5, 10, 15];
    
    offsets.forEach(offset => {
        let cand = minGsuRow + offset;
        if (cand > 0 && cand <= optimalCand) gsuCandidates.push(cand);
    });

    gsuCandidates.push(optimalCand);
    gsuCandidates = [...new Set(gsuCandidates.sort((a, b) => a - b))];

    let tbody = document.querySelector('#simulation-table tbody');
    tbody.innerHTML = '';
    let simResults = [];

    gsuCandidates.forEach(gsu => {
        if (sweepCache[gsu]) {
            simResults.push({ gsu, ...sweepCache[gsu] });
        }
    });

    // Render Table Rows
    simResults.forEach(res => {
        let tr = document.createElement('tr');
        if (res.gsu === minGsuRow) tr.className = 'best-row';

        tr.innerHTML = `
            <td>
                ${res.gsu} 
                ${res.gsu === minGsuRow ? '<span class="status-badge status-optimal">Optimal</span>' : ''}
                ${res.gsu === optimalCand ? '<span class="status-badge" style="margin-left:5px; background: rgba(34, 211, 238, 0.1); color: var(--primary-cyan); border: 1px solid rgba(34, 211, 238, 0.2); font-size: 0.75rem; padding: 2px 6px; border-radius: 4px;">Peak Cap</span>' : ''}
            </td>
            <td>${res.threshold.toLocaleString()}</td>
            <td>$${res.ptCost.toLocaleString()}</td>
            <td>${res.utilRate.toFixed(1)}%</td>
            <td>${res.spilloverB.toFixed(2)}</td>
            <td>$${Math.round(res.paygoCost).toLocaleString()}</td>
            <td><strong>$${Math.round(res.totalCombined).toLocaleString()}</strong></td>
        `;
        tbody.appendChild(tr);
    });
}

function renderChart() {
    const ctx = document.getElementById('tpmChart').getContext('2d');
    const optimalGsu = parseFloat(document.getElementById('metric-optimal_gsu').innerText);
    const threshold = optimalGsu * parseFloat(paramTpmGsu.value);

    let dataPoints = parsedData.map(row => ({ x: row.time, y: row.tpm }));
    let thresholdPoints = parsedData.map(row => ({ x: row.time, y: threshold }));

    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Actual TPM',
                data: dataPoints,
                borderColor: '#22D3EE',
                backgroundColor: 'rgba(34, 211, 238, 0.02)',
                borderWidth: 0.5,
                pointRadius: 0,
                fill: true,
                tension: 0.2,
                order: 2
            }, {
                label: `Threshold (${threshold.toLocaleString()} TPM)`,
                data: thresholdPoints,
                order: 1,
                borderColor: '#F87171',
                borderDash: [5, 5],
                borderWidth: 1.5,
                pointRadius: 0,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#F3F4F6' } },
                zoom: {
                    zoom: {
                        drag: { enabled: true, backgroundColor: 'rgba(34, 211, 238, 0.15)' },
                        mode: 'x',
                        onZoomComplete: () => document.getElementById('reset-zoom').style.display = 'block'
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        tooltipFormat: 'MMM dd, HH:mm',
                        displayFormats: {
                            minute: 'HH:mm',
                            hour: 'HH:mm',
                            day: 'MMM dd',
                            week: 'MMM dd'
                        }
                    },
                    ticks: { color: '#9CA3AF', maxTicksLimit: 12 },
                    grid: { color: 'rgba(255,255,255,0.02)' }
                },
                y: {
                    ticks: {
                        color: '#9CA3AF',
                        callback: function(value) { return (value / 1000000).toFixed(1) + 'M'; }
                    },
                    grid: { color: 'rgba(255,255,255,0.02)' }
                }
            }
        }
    });
}
