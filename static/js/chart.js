/**
 * Chart rendering utility for forex market data
 */
class CandlestickChart {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.chart = null;
        this.candleSeries = null;
        this.volumeSeries = null;
        this.patternMarkers = [];
        this.fvgMarkers = [];
    }

    /**
     * Initialize the chart
     */
    initialize() {
        if (!this.container) {
            console.error('Chart container not found');
            return;
        }

        // Create chart
        this.chart = LightweightCharts.createChart(this.container, {
            width: this.container.clientWidth,
            height: 500,
            layout: {
                backgroundColor: '#131722',
                textColor: '#d1d4dc',
            },
            grid: {
                vertLines: {
                    color: 'rgba(42, 46, 57, 0.5)',
                },
                horzLines: {
                    color: 'rgba(42, 46, 57, 0.5)',
                },
            },
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
            },
        });

        // Add candlestick series
        this.candleSeries = this.chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });

        // Add volume series as a histogram below the chart
        this.volumeSeries = this.chart.addHistogramSeries({
            color: '#26a69a',
            priceFormat: {
                type: 'volume',
            },
            priceScaleId: '',
            scaleMargins: {
                top: 0.8,
                bottom: 0,
            },
        });

        // Handle resize
        window.addEventListener('resize', () => {
            this.chart.resize(this.container.clientWidth, 500);
        });
    }

    /**
     * Load and display candle data
     * @param {string} symbol - Currency symbol
     * @param {string} timeframe - Candle timeframe
     */
    loadCandleData(symbol, timeframe) {
        // Clear existing data
        this.clear();

        // Fetch candle data from API
        fetch(`/api/candles?symbol=${symbol}&timeframe=${timeframe}`)
            .then(response => response.json())
            .then(data => {
                if (!data || data.error) {
                    console.error('Error loading candle data:', data?.error || 'No data');
                    return;
                }

                // Prepare data for chart
                const candleData = data.map(candle => ({
                    time: candle.time,
                    open: candle.open,
                    high: candle.high,
                    low: candle.low,
                    close: candle.close
                }));

                const volumeData = data.map(candle => ({
                    time: candle.time,
                    value: candle.volume,
                    color: candle.close >= candle.open ? '#26a69a' : '#ef5350'
                }));

                // Set data
                this.candleSeries.setData(candleData);
                this.volumeSeries.setData(volumeData);

                // Fit content
                this.chart.timeScale().fitContent();
            })
            .catch(error => {
                console.error('Error fetching candle data:', error);
            });
    }

    /**
     * Show price action patterns on the chart
     * @param {string} symbol - Currency symbol
     * @param {string} timeframe - Pattern timeframe
     */
    showPatterns(symbol, timeframe) {
        fetch(`/api/data/patterns?symbol=${symbol}&timeframe=${timeframe}`)
            .then(response => response.json())
            .then(data => {
                if (!data || data.error) {
                    console.error('Error loading pattern data:', data?.error || 'No data');
                    return;
                }

                // Clear existing pattern markers
                this.patternMarkers.forEach(marker => {
                    this.candleSeries.removePriceLine(marker);
                });
                this.patternMarkers = [];

                // Add pattern markers
                data.forEach(pattern => {
                    const markerColor = this.getPatternColor(pattern.type, pattern.status);
                    const marker = this.candleSeries.createPriceLine({
                        price: pattern.price,
                        color: markerColor,
                        lineWidth: 2,
                        lineStyle: 2, // Dashed line
                        axisLabelVisible: true,
                        title: `${pattern.type} (${pattern.status})`,
                    });
                    this.patternMarkers.push(marker);
                });
            })
            .catch(error => {
                console.error('Error fetching pattern data:', error);
            });
    }

    /**
     * Show fair value gaps on the chart
     * @param {string} symbol - Currency symbol
     * @param {string} timeframe - FVG timeframe
     */
    showFVGs(symbol, timeframe) {
        fetch(`/api/data/fvgs?symbol=${symbol}&timeframe=${timeframe}`)
            .then(response => response.json())
            .then(data => {
                if (!data || data.error) {
                    console.error('Error loading FVG data:', data?.error || 'No data');
                    return;
                }

                // Clear existing FVG markers
                this.fvgMarkers.forEach(marker => {
                    this.candleSeries.removePriceLine(marker);
                });
                this.fvgMarkers = [];

                // Add FVG zones
                data.forEach(fvg => {
                    // Top line of FVG
                    const topLine = this.candleSeries.createPriceLine({
                        price: Math.max(fvg.startPrice, fvg.endPrice),
                        color: 'rgba(76, 175, 80, 0.5)',
                        lineWidth: 1,
                        lineStyle: 0, // Solid line
                        axisLabelVisible: true,
                        title: `FVG Top (${fvg.fillPercentage.toFixed(1)}%)`,
                    });
                    
                    // Bottom line of FVG
                    const bottomLine = this.candleSeries.createPriceLine({
                        price: Math.min(fvg.startPrice, fvg.endPrice),
                        color: 'rgba(76, 175, 80, 0.5)',
                        lineWidth: 1,
                        lineStyle: 0, // Solid line
                        axisLabelVisible: true,
                        title: 'FVG Bottom',
                    });
                    
                    this.fvgMarkers.push(topLine, bottomLine);
                });
            })
            .catch(error => {
                console.error('Error fetching FVG data:', error);
            });
    }

    /**
     * Clear all markers and lines from the chart
     */
    clear() {
        // Clear pattern markers
        this.patternMarkers.forEach(marker => {
            this.candleSeries.removePriceLine(marker);
        });
        this.patternMarkers = [];

        // Clear FVG markers
        this.fvgMarkers.forEach(marker => {
            this.candleSeries.removePriceLine(marker);
        });
        this.fvgMarkers = [];
    }

    /**
     * Get color for a pattern based on type and validation status
     */
    getPatternColor(patternType, status) {
        if (status === 'Invalid') {
            return '#ef5350'; // Red for invalid
        }
        
        if (status === 'Pending') {
            return '#ff9800'; // Orange for pending
        }
        
        // Valid patterns
        switch (patternType) {
            case 'HH':
            case 'HL':
                return '#26a69a'; // Green for bullish
            case 'LH':
            case 'LL':
                return '#ef5350'; // Red for bearish
            case 'BOS':
                return '#42a5f5'; // Blue for BOS
            case 'CHoCH':
                return '#ab47bc'; // Purple for CHoCH
            default:
                return '#ffeb3b'; // Yellow for unknown
        }
    }
}

// Export chart class
window.CandlestickChart = CandlestickChart;
