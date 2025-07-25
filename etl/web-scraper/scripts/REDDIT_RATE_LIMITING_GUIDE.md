# Reddit Rate Limiting Guide

## ✅ **Improvements Added**

### 🎯 **Smart Rate Limiting**
- **Exponential backoff** for 429 errors: 60s → 120s → 240s → 480s
- **Adaptive delays** based on consecutive failures
- **Jitter** to prevent thundering herd problems
- **Configurable retry limits** with intelligent backoff

### 📊 **Enhanced Logging & Recovery**
- **Failed job tracking** with detailed error categorization
- **Resume functionality** from previous failures
- **Real-time progress monitoring** with rate limit status
- **Comprehensive error reporting** in JSON format

### ⚙️ **Configurable Settings**
- `--base-delay`: Base delay between requests (default: 2.0s)
- `--batch-delay`: Delay between chunks (default: 10.0s)  
- `--max-retries`: Maximum retries for failed requests (default: 5)
- `--resume-from-failures`: Resume from a failed jobs JSON file

## 🚀 **Recommended Usage Patterns**

### **For Historical Data Collection (2020-2025)**
```bash
# Conservative approach - most likely to succeed
python scripts/run_full_reddit_scrape.py \
    --start-date 2020-01-01 \
    --end-date 2025-07-23 \
    --base-delay 3.0 \
    --batch-delay 15.0 \
    --max-retries 5 \
    --chunk-days 7 \
    --chunk-limit 25 \
    --chunked
```

### **For Recent Data (Last 6 Months)**
```bash
# Moderate approach
python scripts/run_full_reddit_scrape.py \
    --days-back 180 \
    --base-delay 2.0 \
    --batch-delay 10.0 \
    --chunk-days 14 \
    --chunk-limit 50
```

### **For Testing/Development**
```bash
# Fast testing with small batches
python scripts/run_full_reddit_scrape.py \
    --days-back 7 \
    --base-delay 1.0 \
    --batch-delay 5.0 \
    --chunk-limit 10
```

### **Resume from Failures**
```bash
# If your previous run failed, resume from the failed jobs file
python scripts/run_full_reddit_scrape.py \
    --start-date 2020-01-01 \
    --end-date 2025-07-23 \
    --resume-from-failures logs/reddit_failed_jobs_TIMESTAMP.json \
    --base-delay 5.0 \
    --batch-delay 20.0
```

## 📈 **Rate Limiting Strategy**

### **How It Works**
1. **Base delay**: Always wait between requests (prevents immediate 429s)
2. **429 detection**: When rate limited, increases backoff exponentially
3. **Retry logic**: Up to N retries with increasing delays
4. **Batch delays**: Longer waits between date range chunks
5. **Jitter**: Random delays to distribute load

### **Error Handling**
- **Request errors**: Logged with full context and timestamps
- **Rate limit errors**: Tracked separately with backoff status
- **Failed chunks**: Can be resumed later using JSON file
- **Progress tracking**: Shows successful vs failed chunks

## 🎛️ **Environment Variables**

You can also set these via environment variables:
```bash
export REDDIT_RATE_LIMIT_DELAY=3.0
export REDDIT_BATCH_DELAY=15.0
export REDDIT_MAX_RETRIES=5
export REDDIT_BACKOFF_BASE=60.0
```

## 📊 **Monitoring Progress**

### **Log Files Created**
- `logs/full_reddit_scrape_TIMESTAMP.log` - Main scraping log
- `logs/reddit_failed_jobs_TIMESTAMP.json` - Failed jobs for resume
- `logs/reddit_pure_scraper_TIMESTAMP.log` - Detailed scraper logs

### **Progress Indicators**
- ✅ Successful chunks with story counts
- ⚠️ Rate limit warnings with backoff times
- ❌ Failed chunks with error details
- 📊 Final statistics with error summaries

## 🔧 **Troubleshooting**

### **Still Getting 429 Errors?**
1. **Increase delays**: Double `--base-delay` and `--batch-delay`
2. **Reduce chunk size**: Use `--chunk-limit 10` or smaller
3. **Increase retries**: Use `--max-retries 10`
4. **Use smaller date ranges**: `--chunk-days 3`

### **No Stories Found?**
1. Check if subreddit name is correct (case-sensitive)
2. Verify date ranges have activity
3. Check Reddit API access permissions
4. Review failed jobs JSON for specific errors

### **Resume from Failures**
1. Find the failed jobs JSON file in `logs/`
2. Use `--resume-from-failures path/to/file.json`
3. System will skip previously failed ranges initially
4. Consider using more conservative rate limits when resuming

## 💡 **Best Practices**

1. **Start conservative**: Use high delays for initial runs
2. **Monitor logs**: Watch for 429 patterns and adjust
3. **Use chunking**: Always chunk large date ranges
4. **Save failed jobs**: Keep JSON files for resuming
5. **Run during off-peak**: Less competition for API resources