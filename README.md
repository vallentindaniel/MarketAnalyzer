# Market Analyzer: Forex Trading Analysis Tool

A web application for forex market analysis that helps traders identify price action patterns, Fair Value Gaps (FVGs), and potential trading opportunities through advanced data processing and visualization.

## Features

- Upload and process forex candle data from CSV files
- Automatically generate higher timeframe candles (5m, 15m, 30m, 1H, 4H)
- Identify and validate price action patterns (HH, HL, LH, LL, BOS, CHoCH)
- Detect Fair Value Gaps and calculate fill percentages
- Find trade opportunities based on CHoCH patterns and FVGs
- Track trade statistics with 1:2 risk-reward ratio
- Interactive chart visualization

## Key Technologies

- Backend: Python/Flask
- Database: SQLite or MySQL (configurable)
- Frontend: JavaScript with LightweightCharts
- UI: Bootstrap CSS

## Installation

1. Clone the repository
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure environment variables (see Configuration section)
4. Initialize the database:
   ```
   python init/db_init.py
   ```
5. Run the application:
   ```
   python main.py
   ```

## Configuration

The application can be configured using environment variables:

- `DB_TYPE`: Database type to use ('sqlite' or 'mysql', default: 'sqlite')
- `MYSQL_HOST`: MySQL host (default: 'localhost')
- `MYSQL_PORT`: MySQL port (default: 3306)
- `MYSQL_USER`: MySQL username
- `MYSQL_PASSWORD`: MySQL password
- `MYSQL_DATABASE`: MySQL database name
- `SESSION_SECRET`: Secret key for Flask sessions

Create a `.env` file in the root directory with these variables.

## Database Structure

The application uses a hierarchical candle model to represent different timeframes:
- 1m candles link to 5m candles
- 5m candles link to 15m candles
- 15m candles link to 30m candles
- 30m candles link to 1H candles
- 1H candles link to 4H candles

This is implemented through parent-child relationships using foreign keys.

## Usage

1. Start the application
2. Upload a CSV file with 1-minute forex data
3. The system will automatically generate higher timeframe candles
4. Use the "Link Timeframes" button if candles aren't properly linked
5. Analyze price action patterns using the Price Action tab
6. Identify Fair Value Gaps using the FVG tab
7. Find trading opportunities in the Trade Opportunities tab

## Data Format

The CSV file should contain the following columns:
- timestamp: Date and time
- open: Opening price
- high: High price
- low: Low price
- close: Closing price
- volume: Volume

## Development

To run the application in development mode:
```
flask run --host=0.0.0.0 --port=5000 --debug
```

Or simply:
```
python main.py
```

## License

MIT