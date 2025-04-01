/**
 * Market Analyzer Application
 * Main JavaScript functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize chart
    const chart = new CandlestickChart('chart-container');
    chart.initialize();
    
    // Initialize tab functionality
    const tabs = document.querySelectorAll('.nav-link');
    tabs.forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            // Show the selected tab
            const tabId = this.getAttribute('href');
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('show', 'active');
            });
            document.querySelector(tabId).classList.add('show', 'active');
            
            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // Handle file upload
    const uploadForm = document.getElementById('upload-form');
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const symbol = document.getElementById('currency-select').value;
        formData.append('symbol', symbol);
        
        // Show loading state
        document.getElementById('upload-status').textContent = 'Uploading...';
        document.getElementById('upload-btn').disabled = true;
        
        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showAlert('danger', `Error: ${data.error}`);
                document.getElementById('upload-status').textContent = 'Failed to upload';
            } else {
                showAlert('success', `Successfully processed ${data.candleCount} candles`);
                document.getElementById('upload-status').textContent = 'Upload complete';
                
                // Load chart data
                const timeframe = document.getElementById('timeframe-select').value;
                chart.loadCandleData(symbol, timeframe);
                
                // Enable analysis buttons
                document.querySelectorAll('.analysis-btn').forEach(btn => {
                    btn.disabled = false;
                });
            }
            document.getElementById('upload-btn').disabled = false;
        })
        .catch(error => {
            console.error('Upload error:', error);
            showAlert('danger', 'Upload failed. See console for details.');
            document.getElementById('upload-status').textContent = 'Upload failed';
            document.getElementById('upload-btn').disabled = false;
        });
    });
    
    // Handle timeframe change for chart
    document.getElementById('timeframe-select').addEventListener('change', function() {
        const symbol = document.getElementById('currency-select').value;
        const timeframe = this.value;
        chart.loadCandleData(symbol, timeframe);
    });
    
    // Handle Price Action Analysis
    document.getElementById('analyze-price-action-btn').addEventListener('click', function() {
        const symbol = document.getElementById('currency-select').value;
        const pivotTimeframe = document.getElementById('pivot-timeframe-select').value;
        const timeframes = Array.from(document.querySelectorAll('input[name="pa-timeframe"]:checked')).map(cb => cb.value);
        
        if (timeframes.length === 0) {
            showAlert('warning', 'Please select at least one timeframe for analysis');
            return;
        }
        
        // Show loading state
        this.disabled = true;
        this.textContent = 'Analyzing...';
        
        fetch('/api/analyze/price-action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                symbol: symbol,
                timeframes: timeframes,
                pivotTimeframe: pivotTimeframe
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showAlert('danger', `Error: ${data.error}`);
            } else {
                showAlert('success', 'Price action analysis completed');
                updatePriceActionStats(data);
                
                // Show patterns on chart
                chart.showPatterns(symbol, pivotTimeframe);
            }
            this.disabled = false;
            this.textContent = 'Analyze Price Action';
        })
        .catch(error => {
            console.error('Analysis error:', error);
            showAlert('danger', 'Analysis failed. See console for details.');
            this.disabled = false;
            this.textContent = 'Analyze Price Action';
        });
    });
    
    // Handle FVG Analysis
    document.getElementById('analyze-fvg-btn').addEventListener('click', function() {
        const symbol = document.getElementById('currency-select').value;
        const timeframe = document.getElementById('fvg-timeframe-select').value;
        
        // Show loading state
        this.disabled = true;
        this.textContent = 'Analyzing...';
        
        fetch('/api/analyze/fvg', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                symbol: symbol,
                timeframe: timeframe
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showAlert('danger', `Error: ${data.error}`);
            } else {
                showAlert('success', data.message);
                
                // Switch to this timeframe and show FVGs
                document.getElementById('timeframe-select').value = timeframe;
                chart.loadCandleData(symbol, timeframe);
                chart.showFVGs(symbol, timeframe);
            }
            this.disabled = false;
            this.textContent = 'Find Fair Value Gaps';
        })
        .catch(error => {
            console.error('FVG analysis error:', error);
            showAlert('danger', 'Analysis failed. See console for details.');
            this.disabled = false;
            this.textContent = 'Find Fair Value Gaps';
        });
    });
    
    // Handle Trade Opportunities Analysis
    document.getElementById('analyze-opportunities-btn').addEventListener('click', function() {
        const symbol = document.getElementById('currency-select').value;
        const chochTimeframe = document.getElementById('choch-timeframe-select').value;
        const fvgTimeframe = document.getElementById('fvg-opp-timeframe-select').value;
        
        // Show loading state
        this.disabled = true;
        this.textContent = 'Analyzing...';
        
        fetch('/api/analyze/opportunities', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                symbol: symbol,
                chochTimeframe: chochTimeframe,
                fvgTimeframe: fvgTimeframe
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showAlert('danger', `Error: ${data.error}`);
            } else {
                showAlert('success', data.message);
                loadTradeOpportunities();
            }
            this.disabled = false;
            this.textContent = 'Find Trade Opportunities';
        })
        .catch(error => {
            console.error('Opportunities analysis error:', error);
            showAlert('danger', 'Analysis failed. See console for details.');
            this.disabled = false;
            this.textContent = 'Find Trade Opportunities';
        });
    });
    
    // Load trade opportunities
    function loadTradeOpportunities() {
        fetch('/api/data/opportunities')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Error loading opportunities:', data.error);
                    return;
                }
                
                // Render opportunities table
                const tableBody = document.getElementById('opportunities-table-body');
                tableBody.innerHTML = '';
                
                if (data.length === 0) {
                    tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No trade opportunities found</td></tr>';
                    return;
                }
                
                data.forEach(opp => {
                    const row = document.createElement('tr');
                    row.className = getStatusClass(opp.status);
                    
                    row.innerHTML = `
                        <td>${new Date(opp.creationTime * 1000).toLocaleString()}</td>
                        <td>${opp.patternType} (${opp.patternTimeframe})</td>
                        <td>${opp.fvgTimeframe}</td>
                        <td>${opp.entryPrice.toFixed(5)}</td>
                        <td>${opp.stopLoss.toFixed(5)}</td>
                        <td>${opp.takeProfit.toFixed(5)}</td>
                        <td><span class="badge ${getStatusBadgeClass(opp.status)}">${opp.status}</span></td>
                    `;
                    
                    tableBody.appendChild(row);
                });
                
                // Load trade statistics
                loadTradeStatistics();
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }
    
    // Load trade statistics
    function loadTradeStatistics() {
        fetch('/api/statistics/trades')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Error loading statistics:', data.error);
                    return;
                }
                
                // Update statistics in the UI
                document.getElementById('total-opportunities').textContent = data.totalOpportunities;
                document.getElementById('win-count').textContent = data.winCount;
                document.getElementById('loss-count').textContent = data.lossCount;
                document.getElementById('pending-count').textContent = data.pendingCount;
                document.getElementById('win-rate').textContent = `${data.winRate}%`;
                document.getElementById('expectancy').textContent = data.expectancy;
                
                // Update timeframe statistics
                const tfStatsBody = document.getElementById('timeframe-stats-body');
                tfStatsBody.innerHTML = '';
                
                if (Object.keys(data.timeframeStats).length === 0) {
                    tfStatsBody.innerHTML = '<tr><td colspan="5" class="text-center">No statistics available</td></tr>';
                    return;
                }
                
                for (const [tf, stats] of Object.entries(data.timeframeStats)) {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${tf}</td>
                        <td>${stats.count}</td>
                        <td>${stats.wins}</td>
                        <td>${stats.losses}</td>
                        <td>${stats.winRate}%</td>
                    `;
                    tfStatsBody.appendChild(row);
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }
    
    // Update price action statistics display
    function updatePriceActionStats(data) {
        // Update validation stats
        document.getElementById('valid-patterns').textContent = data.validationStats.valid;
        document.getElementById('invalid-patterns').textContent = data.validationStats.invalid;
        document.getElementById('pending-patterns').textContent = data.validationStats.pending;
        
        // Update pattern counts by timeframe
        const patternStatsBody = document.getElementById('pattern-stats-body');
        patternStatsBody.innerHTML = '';
        
        for (const [timeframe, counts] of Object.entries(data.patternCounts)) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${timeframe}</td>
                <td>${counts.HH}</td>
                <td>${counts.HL}</td>
                <td>${counts.LH}</td>
                <td>${counts.LL}</td>
                <td>${counts.BOS}</td>
                <td>${counts.CHoCH}</td>
                <td>${data.patternsByTimeframe[timeframe] || 0}</td>
            `;
            patternStatsBody.appendChild(row);
        }
    }
    
    // Helper function to show alerts
    function showAlert(type, message) {
        const alertContainer = document.getElementById('alert-container');
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        alertContainer.appendChild(alert);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => alert.remove(), 150);
        }, 5000);
    }
    
    // Helper function to get row class based on status
    function getStatusClass(status) {
        switch (status) {
            case 'Win':
                return 'table-success';
            case 'Loss':
                return 'table-danger';
            case 'Executed':
                return 'table-warning';
            default:
                return '';
        }
    }
    
    // Helper function to get badge class based on status
    function getStatusBadgeClass(status) {
        switch (status) {
            case 'Win':
                return 'bg-success';
            case 'Loss':
                return 'bg-danger';
            case 'Executed':
                return 'bg-warning';
            case 'Pending':
                return 'bg-info';
            case 'Canceled':
                return 'bg-secondary';
            default:
                return 'bg-secondary';
        }
    }
});
