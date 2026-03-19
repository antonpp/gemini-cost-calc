// Model Presets Data
const MODEL_PRESETS = {
    "Gemini 3.1 Pro (Preview)": {
        tpmPerGsu: 30000,
        gsuCost: 2000,
        inputRate: 2.00,
        outputRate: 12.00,
        paygoMult: 1.8,
        maxPrio: 2000000,
        maxStd: 2000000
    },
    "Gemini 3 Flash (Preview)": {
        tpmPerGsu: 120900,
        gsuCost: 2000,
        inputRate: 0.50,
        outputRate: 3.00,
        paygoMult: 1.8,
        maxPrio: 10000000,
        maxStd: 10000000
    },
    "Gemini 3.1 Flash-Lite (Preview)": {
        tpmPerGsu: 241800,
        gsuCost: 2000,
        inputRate: 0.25,
        outputRate: 1.50,
        paygoMult: 1.8,
        maxPrio: 10000000,
        maxStd: 10000000
    }
};

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

// Tiers toggles & bounds sliders
const enablePt = document.getElementById('enable-pt');
const enablePriority = document.getElementById('enable-priority');
const enableStandard = document.getElementById('enable-standard');
const paramMaxPrio = document.getElementById('param-max_priority');
const paramMaxStd = document.getElementById('param-max_standard');

const sliders = [paramTpmGsu, paramGsuCost, paramInputRate, paramOutputRate, paramRatio, paramPaygoMult, paramMaxPrio, paramMaxStd];

// Event Listeners for file upload
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFileSelect);

// Auto-run test if requested via URL param (Local server required)
document.addEventListener('DOMContentLoaded', () => {
    initPresets();

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

// Toggles Trigger Updates
[enablePt, enablePriority, enableStandard].forEach(cb => {
    cb.addEventListener('change', () => {
        if (parsedData.length > 0) {
            runSimulation();
            renderChart();
        }
    });
});

// Unlimited Toggles listeners
const unlimitedPriority = document.getElementById('unlimited-priority');
const unlimitedStandard = document.getElementById('unlimited-standard');

[unlimitedPriority, unlimitedStandard].forEach(cb => {
    cb.addEventListener('change', (e) => {
        const isPriority = e.target.id === 'unlimited-priority';
        const slider = isPriority ? paramMaxPrio : paramMaxStd;
        const label = document.getElementById(isPriority ? 'val-max_priority' : 'val-max_standard');
        
        slider.disabled = e.target.checked;
        if (e.target.checked) {
            label.innerText = "Unlimited";
        } else {
            updateLabel(slider.id);
        }
        if (parsedData.length > 0) {
            runSimulation();
            renderChart();
        }
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

function initPresets() {
    const select = document.getElementById('model-preset');
    if (!select) return;

    // Populate options
    for (const model in MODEL_PRESETS) {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        select.appendChild(option);
    }

    // Listener
    select.addEventListener('change', (e) => {
        applyPreset(e.target.value);
    });

    // Apply first preset
    applyPreset(Object.keys(MODEL_PRESETS)[0]);
}

function applyPreset(modelName) {
    const preset = MODEL_PRESETS[modelName];
    if (!preset) return;

    paramTpmGsu.value = preset.tpmPerGsu;
    paramGsuCost.value = preset.gsuCost;
    paramInputRate.value = preset.inputRate;
    paramOutputRate.value = preset.outputRate;
    paramPaygoMult.value = preset.paygoMult;
    
    paramMaxPrio.value = preset.maxPrio;
    paramMaxStd.value = preset.maxStd;

    // Uncheck unlimited
    document.getElementById('unlimited-priority').checked = false;
    document.getElementById('unlimited-standard').checked = false;
    paramMaxPrio.disabled = false;
    paramMaxStd.disabled = false;

    // Update labels
    updateLabel('param-tpm_gsu');
    updateLabel('param-gsu_cost');
    updateLabel('param-input_rate');
    updateLabel('param-output_rate');
    updateLabel('param-paygo_mult');
    updateLabel('param-max_priority');
    updateLabel('param-max_standard');
}


function updateLabel(id) {
    if (id === 'param-tpm_gsu') document.getElementById('val-tpm_gsu').innerText = Number(paramTpmGsu.value).toLocaleString();
    if (id === 'param-gsu_cost') document.getElementById('val-gsu_cost').innerText = `$${Number(paramGsuCost.value).toLocaleString()}`;
    if (id === 'param-input_rate') document.getElementById('val-input_rate').innerText = `$${parseFloat(paramInputRate.value).toFixed(2)}`;
    if (id === 'param-output_rate') document.getElementById('val-output_rate').innerText = `$${parseFloat(paramOutputRate.value).toFixed(2)}`;
    if (id === 'param-paygo_mult') document.getElementById('val-paygo_mult').innerText = `${parseFloat(paramPaygoMult.value).toFixed(1)}x`;
    if (id === 'param-max_priority') document.getElementById('val-max_priority').innerText = Number(paramMaxPrio.value).toLocaleString();
    if (id === 'param-max_standard') document.getElementById('val-max_standard').innerText = Number(paramMaxStd.value).toLocaleString();
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

    // Toggles & Bounds
    const ptEnabled = enablePt.checked;
    const prioEnabled = enablePriority.checked;
    const stdEnabled = enableStandard.checked;
    const maxPrioTpm = document.getElementById('unlimited-priority').checked ? 500000000 : parseFloat(paramMaxPrio.value);
    const maxStdTpm = document.getElementById('unlimited-standard').checked ? 500000000 : parseFloat(paramMaxStd.value);

    // Pre-aggregations
    let totalTokens = parsedData.reduce((sum, row) => sum + row.tpm * detectedM, 0);
    let peakTpm = Math.max(...parsedData.map(row => row.tpm));

    document.getElementById('metric-total_tokens').innerText = (totalTokens / 1_000_000_000).toFixed(2) + " B";
    document.getElementById('metric-peak_tpm').innerText = (peakTpm / 1_000_000).toFixed(1) + " M";

    // Dynamic Sweep to find precise absolute optimal GSU
    let optimalCand = ptEnabled ? Math.ceil(peakTpm / tpmPerGsu) : 0;
    let minCost = Infinity;
    let minGsuRow = ptEnabled ? 1 : 0;
    let sweepCache = {};

    const startGsu = ptEnabled ? 1 : 0;
    const endGsu = ptEnabled ? optimalCand : 0;

    for (let gsu = startGsu; gsu <= endGsu; gsu++) {
        let ptThreshold = gsu * tpmPerGsu;
        
        let prioThreshold = ptThreshold;
        if (prioEnabled) prioThreshold += maxPrioTpm;

        let stdThreshold = prioThreshold + maxStdTpm;

        let ptCovered = 0;
        let prioCovered = 0;
        let stdCovered = 0;
        let overflow429 = 0;

        parsedData.forEach(row => {
            let rem = row.tpm;

            // Tier 1 (PT)
            let currentPt = ptEnabled ? Math.min(rem, ptThreshold) : 0;
            ptCovered += currentPt * detectedM;
            rem -= currentPt;

            // Tier 2 (Priority)
            let currentPrio = prioEnabled ? Math.min(rem, maxPrioTpm) : 0;
            prioCovered += currentPrio * detectedM;
            rem -= currentPrio;

            // Tier 3 (Standard)
            let currentStd = stdEnabled ? Math.min(rem, maxStdTpm) : 0;
            stdCovered += currentStd * detectedM;
            rem -= currentStd;

            // Overflow 429
            overflow429 += rem * detectedM;
        });

        // Costs
        let ptCost = gsu * gsuCost; 
        
        let prioInput = prioCovered * inputRatio;
        let prioOutput = prioCovered * outputRatio;
        let prioCost = ((prioInput / 1000000) * inputRate + (prioOutput / 1000000) * outputRate) * paygoMult;

        let stdInput = stdCovered * inputRatio;
        let stdOutput = stdCovered * outputRatio;
        let stdCost = ((stdInput / 1000000) * inputRate + (stdOutput / 1000000) * outputRate); // No multiplier

        let totalCombined = ptCost + prioCost + stdCost;

        let totalAvailable = ptThreshold * detectedM * parsedData.length;
        let utilRate = totalAvailable > 0 ? (ptCovered / totalAvailable) * 100 : 0;

        sweepCache[gsu] = {
            threshold: ptThreshold,
            ptCost,
            utilRate,
            prioCoveredB: prioCovered / 1_000_000_000,
            prioCost,
            stdCoveredB: stdCovered / 1_000_000_000,
            stdCost,
            overflowB: overflow429 / 1_000_000_000,
            totalCombined
        };

        if (totalCombined < minCost) {
            minCost = totalCombined;
            minGsuRow = gsu;
        }
    }

    document.getElementById('metric-optimal_gsu').innerText = ptEnabled ? minGsuRow : "N/A (Disabled)";
    document.getElementById('metric-total_cost').innerText = `$${Math.round(minCost).toLocaleString()}`;

    // Generate Display Candidates Grid
    let gsuCandidates = ptEnabled ? [5, 10, 20, 24, 50, 100, 200] : [0];
    let offsets = [-15, -10, -5, 0, 5, 10, 15];
    
    if (ptEnabled) {
        offsets.forEach(offset => {
            let cand = minGsuRow + offset;
            if (cand > 0 && cand <= optimalCand) gsuCandidates.push(cand);
        });
        gsuCandidates.push(optimalCand);
    }
    
    gsuCandidates = [...new Set(gsuCandidates.sort((a, b) => a - b))];

    let tbody = document.querySelector('#simulation-table tbody');
    tbody.innerHTML = '';

    gsuCandidates.forEach(gsu => {
        if (sweepCache[gsu]) {
            let res = sweepCache[gsu];
            let tr = document.createElement('tr');
            if (ptEnabled && gsu === minGsuRow) tr.className = 'best-row';

            tr.innerHTML = `
                <td>
                    ${gsu} 
                    ${ptEnabled && gsu === minGsuRow ? '<span class="status-badge status-optimal">Optimal</span>' : ''}
                    ${ptEnabled && gsu === optimalCand ? '<span class="status-badge" style="margin-left:5px; background: rgba(34, 211, 238, 0.1); color: var(--primary-cyan); border: 1px solid rgba(34, 211, 238, 0.2); font-size: 0.75rem; padding: 2px 6px; border-radius: 4px;">Peak Cap</span>' : ''}
                </td>
                <td>${res.threshold.toLocaleString()}</td>
                <td>$${res.ptCost.toLocaleString()}</td>
                <td>${res.utilRate.toFixed(1)}%</td>
                <td>${(res.prioCoveredB + res.stdCoveredB).toFixed(2)} B</td>
                <td>$${Math.round(res.prioCost + res.stdCost).toLocaleString()}</td>
                <td><strong>$${Math.round(res.totalCombined).toLocaleString()}</strong></td>
            `;
            tbody.appendChild(tr);
        }
    });
}

function renderChart() {
    const ctx = document.getElementById('tpmChart').getContext('2d');
    const optimalGsuEl = document.getElementById('metric-optimal_gsu').innerText;
    
    let optimalGsu = 0;
    if (optimalGsuEl !== "N/A (Disabled)") {
        optimalGsu = parseFloat(optimalGsuEl) || 0;
    }

    const ptEnabled = enablePt.checked;
    const prioEnabled = enablePriority.checked;
    const tpmPerGsu = parseFloat(paramTpmGsu.value);

    const unlimitedPrio = document.getElementById('unlimited-priority').checked;
    const unlimitedStd = document.getElementById('unlimited-standard').checked;

    let ptLimit = ptEnabled ? optimalGsu * tpmPerGsu : 0;
    let prioLimit = ptLimit + (prioEnabled ? (unlimitedPrio ? 500000000 : parseFloat(paramMaxPrio.value)) : 0);
    let stdLimit = prioLimit + (unlimitedStd ? 500000000 : parseFloat(paramMaxStd.value));

    // Calculate Y axis scale max to prevent unlimited lines from flattening data peaks
    const peakTpm = Math.max(...parsedData.map(row => row.tpm));
    let maxDisplay = peakTpm;
    if (ptEnabled && ptLimit < peakTpm * 3) maxDisplay = Math.max(maxDisplay, ptLimit);
    if (prioEnabled && prioLimit < peakTpm * 3) maxDisplay = Math.max(maxDisplay, prioLimit);
    // Ignore absurdly high unlimited lines
    const stdEnabledVis = document.getElementById('enable-standard').checked;
    if (stdEnabledVis && stdLimit < peakTpm * 3) maxDisplay = Math.max(maxDisplay, stdLimit);
    const yMax = maxDisplay * 1.1;

    let dataPoints = parsedData.map(row => ({ x: row.time, y: row.tpm }));

    let datasets = [{
        label: 'Actual TPM',
        data: dataPoints,
        borderColor: '#22D3EE',
        backgroundColor: 'rgba(34, 211, 238, 0.02)',
        borderWidth: 0.5,
        pointRadius: 0,
        fill: true,
        tension: 0.2,
        order: 5
    }];

    if (ptEnabled && ptLimit > 0) {
        datasets.push({
            label: `PT Limit (${ptLimit.toLocaleString()})`,
            data: parsedData.map(row => ({ x: row.time, y: ptLimit })),
            borderColor: '#F87171', // Red
            borderDash: [5, 5],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
            order: 1
        });
    }

    if (prioEnabled) {
        datasets.push({
            label: `Priority Limit (${prioLimit.toLocaleString()})`,
            data: parsedData.map(row => ({ x: row.time, y: prioLimit })),
            borderColor: '#FBBF24', // Amber
            borderDash: [5, 5],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
            order: 2
        });
    }

    const stdEnabledLayout = document.getElementById('enable-standard').checked;
    if (stdEnabledLayout) {
        datasets.push({
            label: `Standard Limit (${stdLimit.toLocaleString()})`,
            data: parsedData.map(row => ({ x: row.time, y: stdLimit })),
            borderColor: '#10B981', // Emerald
            borderDash: [5, 5],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
            order: 3
        });
    }

    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: { datasets },
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
                    max: yMax,
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
