# Database Configuration Guide

The Market Analyzer application uses PostgreSQL database. This guide provides detailed information on how to configure the database connection.

## PostgreSQL Configuration

To configure PostgreSQL, you'll need to set the following environment variable:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection URL | None | Yes |

### Connection URL Format

The `DATABASE_URL` should follow this format:
```
postgresql://username:password@host:port/database
```

Example:
```
postgresql://myuser:mypassword@localhost:5432/market_analyzer
```

### Using with Replit Database

If you're using Replit's built-in PostgreSQL database, the `DATABASE_URL` is automatically set as an environment variable.

## Setting Up Environment Variables

1. Create a `.env` file in the root directory of the application
2. Add the necessary environment variables
3. The application will automatically load these variables on startup

Example `.env` file:
```
DATABASE_URL=postgresql://myuser:mypassword@localhost:5432/market_analyzer
SESSION_SECRET=your_secure_session_key
```

## Database Schema

The Market Analyzer uses a relational database schema with the following tables:

1. **Candles**: Stores price data in various timeframes
   - Primary key: `candle_id`
   - Foreign key relationship to itself via `parent_candle_id`

2. **PriceActionPatterns**: Stores price action pattern data
   - Primary key: `pattern_id`
   - Foreign key relationship to `Candles` via `candle_id`

3. **FairValueGaps**: Stores FVG data
   - Primary key: `fvg_id`
   - Foreign key relationships to:
     - `PriceActionPatterns` via `pattern_id`
     - `Candles` via `candle_start_id` and `candle_end_id`

4. **TradeOpportunities**: Stores trade opportunity data
   - Primary key: `opportunity_id`
   - Foreign key relationships to:
     - `PriceActionPatterns` via `choch_pattern_id`
     - `FairValueGaps` via `fvg_id`

## Database Initialization

The database is automatically initialized when you run the application for the first time. If you need to manually initialize the database, run:

```bash
python init/db_init.py
```

This script will:
1. Create the database if it doesn't exist
2. Create all required tables based on the application models
3. Set up any initial data required for the application

## Troubleshooting Database Connection Issues

1. Ensure PostgreSQL is running on the specified host and port
2. Verify the username and password are correct
3. Make sure the database exists
4. Check that the user has the necessary permissions

Common error: "FATAL: database 'market_analyzer' does not exist"
Solution: Create the database manually before connecting:

```sql
CREATE DATABASE market_analyzer;
```