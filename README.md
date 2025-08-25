# 🌐 UK Web Change Tracker

Minimal but extensible project to quantify **"What changed on the UK web after July 25, 2025?"**  
Built with Flask, MongoDB, and Cloudflare Radar APIs.

---

## 🚀 Features (MVP)
- **Live ingestion** from Cloudflare Radar:
  - HTTP Requests (normalized time series)
  - Top Domains (with categories)
  - Layer 3 attack timeseries (bitrate)
  - Bot traffic analysis
- **Analytics**:
  - Pre/Post window deltas (Traffic Shift Index)
  - Rank promotions/demotions
  - Monthly averages, since-event summaries
- **Age-gating checker**: Curated list + automatic flagging in Top 100 domains
- **API Endpoints**: `/api/top-domains`, `/api/timeseries`, `/api/changes`, `/api/window-stats`, `/api/age-gate`, etc.
- **Dashboard**: Modern Flask templates with Tailwind CSS + Chart.js (traffic, top domains, age-gate, L3, OONI, Trends, Tor)
- **Tests**: Ingest (monkeypatched), analytics, routes, web render

---

## 🔄 Data Flow & Architecture

### **How Data Gets Into Your System**

**1. Data Ingestion (CLI Commands)**
```bash
# Fetch HTTP traffic data for last 90 days
python src/cli.py fetch-cloudflare --kind http --country GB --days 90

# Fetch L3 attack data for last 90 days  
python src/cli.py fetch-cloudflare --kind l3 --country GB --days 90 --direction target

# Fetch bot traffic data for last 30 days
python src/cli.py fetch-cloudflare --kind bots --country GB --days 30

# Fetch top domains ranking
python src/cli.py fetch-cloudflare --kind top --country GB --limit 100
```

**What Happens During Ingestion:**
- CLI calls Cloudflare Radar APIs
- Data gets parsed and normalized into consistent format
- Stored in MongoDB collections with proper indexing
- Supports fallback strategies for API failures

**2. Data Storage (MongoDB Collections)**
- `traffic_ts`: HTTP requests, bot traffic timeseries
- `l3_ts`: Layer 3 attack data (target/origin)
- `bot_traffic`: Bot traffic percentages
- `domain_rank`: Top domain rankings
- `ooni_tool_ok`: OONI reachability data

**Data Structure Example:**
```json
{
  "country": "GB",
  "metric": "http_requests_norm", 
  "ts": "2025-07-19T19:00:00Z",
  "value": 1.23
}
```

### **How Charts Get Data**

**Frontend JavaScript** → **API Endpoints** → **MongoDB Queries**

**Example Flow for HTTP Chart:**
```javascript
// 1. Frontend calculates time window
const since = new Date(eventDate.getTime() - 15 * 24 * 60 * 60 * 1000).toISOString();
const until = new Date(eventDate.getTime() + 15 * 24 * 60 * 60 * 1000).toISOString();

// 2. Makes API call
const payload = await getJSON(`/api/timeseries?country=GB&metric=http_requests_norm&since=${since}&until=${until}`);

// 3. API endpoint queries MongoDB
// 4. Returns data to frontend
// 5. Chart renders with the data
```

**API Endpoints:**
- `/api/timeseries` - HTTP, L3, bot traffic data
- `/api/ooni/tor` - OONI reachability data
- `/api/top-domains/age-gated` - Domain rankings
- `/api/age-gate/timeseries` - Age gate compliance

### **How to Feed Charts New Data**

#### **Option A: Fetch More Historical Data**
```bash
# Get data for a longer time period
python src/cli.py fetch-cloudflare --kind http --country GB --days 180  # 6 months
python src/cli.py fetch-cloudflare --kind l3 --country GB --days 180 --direction target
python src/cli.py fetch-cloudflare --kind l3 --country GB --days 180 --direction origin
python src/cli.py fetch-cloudflare --kind bots --country GB --days 180
```

#### **Option B: Fetch Data for Different Countries**
```bash
# Get data for other countries
python src/cli.py fetch-cloudflare --kind http --country US --days 90
python src/cli.py fetch-cloudflare --kind l3 --country DE --days 90 --direction target
```

#### **Option C: Fetch Data for Specific Date Ranges**
```bash
# Get data for specific periods
python src/cli.py fetch-cloudflare --kind http --country GB --days 30  # Last month only
python src/cli.py fetch-cloudflare --kind l3 --country GB --days 14 --direction origin  # Last 2 weeks
```

#### **For Real-time Updates**
```bash
# Run ingestion commands periodically
python src/cli.py fetch-cloudflare --kind http --country GB --days 7  # Last week
python src/cli.py fetch-cloudflare --kind l3 --country GB --days 7 --direction target
```

#### **For Historical Analysis**
```bash
# Fetch longer periods for trend analysis
python src/cli.py fetch-cloudflare --kind http --country GB --days 365  # Full year
```

### **Current Data Reality vs. Chart Display**

**What You Currently Have:**
- **HTTP**: July 19 - August 15 (28 days)
- **L3**: July 19 - August 18 (30 days)
- **Bot Traffic**: July 19 - August 18 (30 days)

**What Charts Are Requesting:**
- **Current Setting**: 30 days centered on event (July 10 - August 9)
- **Benefit**: Charts now show only the time range where you actually have data

### **Data Refresh Strategy**

**The beauty of this system**: Once you fetch new data into MongoDB, the charts automatically get it through the existing API endpoints - no code changes needed!

**Key Benefits:**
- **Separation of Concerns**: Ingestion logic separate from visualization logic
- **Automatic Updates**: Charts automatically use new data as it's ingested
- **Flexible Time Windows**: Easy to adjust chart time ranges in `scripts.html`
- **Scalable**: Add new data sources without changing chart code

---

## 🏗️ Project Structure

```
src/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration management
│   ├── api/                 # API endpoints
│   │   ├── __init__.py      # API blueprint registration
│   │   ├── routes.py        # Main API routes
│   │   ├── events.py        # Event management
│   │   ├── timeseries.py    # Time series data
│   │   ├── top_domains.py   # Top domains API
│   │   ├── age_gate.py      # Age gate compliance
│   │   ├── ooni.py          # OONI reachability
│   │   ├── trends.py        # Google Trends
│   │   └── health.py        # Health checks
│   ├── web/                 # Web dashboard
│   │   ├── __init__.py      # Web blueprint registration
│   │   ├── routes.py        # Web routes
│   │   └── templates/       # Modular template structure
│   │       ├── base.html    # Base template (head, styles, scripts)
│   │       ├── index.html   # Main dashboard (extends base)
│   │       ├── header.html  # Header component
│   │       ├── controls.html # Controls component
│   │       ├── http_chart.html # HTTP chart component
│   │       ├── l3_attacks.html # L3 attacks component
│   │       ├── ooni.html    # OONI component
│   │       ├── bot_traffic.html # Bot traffic component
│   │       ├── domains_age_gate.html # Domains & age gate
│   │       ├── data_insights.html # Data insights
│   │       ├── tor_metrics.html # Tor metrics
│   │       ├── google_trends.html # Google Trends
│   │       ├── footer.html  # Footer component
│   │       └── scripts.html # JavaScript functionality
│   ├── ingest/              # Data ingestion
│   │   ├── cloudflare.py    # Cloudflare Radar API
│   │   └── ooni.py          # OONI reachability
│   ├── db/                  # Database layer
│   │   └── mongo.py         # MongoDB operations
│   ├── analytics/           # Data analysis
│   │   ├── joiners.py       # Data joining utilities
│   │   ├── ranks.py         # Ranking analysis
│   │   └── windows.py       # Time window analysis
│   ├── crypto/              # Encryption utilities
│   │   └── encrypt.py       # Fernet encryption
│   └── data/                # Data models
│       └── age_gate_curated.py # Curated age gate data
├── cli.py                   # Command line interface
└── tests/                   # Test suite
    ├── conftest.py          # Test configuration
    ├── fixtures.py          # Test fixtures
    └── test_*.py            # Individual test modules
```

---

## ⚙️ Setup

### 0) Clone and create a virtualenv

```bash
git clone https://github.com/yourname/uk-web-change-tracker.git
cd uk-web-change-tracker
python -m venv venv
source venv/bin/activate   # (or venv\Scripts\activate on Windows)
```

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Configure environment

Copy the example file and edit secrets:

```bash
cp .env.example .env
```

Fill in at minimum:
- `SECRET_KEY`, `FERNET_KEY`, `HMAC_KEY`
- `MONGODB_URI` and `MONGO_DB`
- `CLOUDFLARE_API_TOKEN`

Generate fresh keys if needed:

```bash
python src/cli.py secret gen-key
python src/cli.py secret gen-key --hmac
```

### 3) Run the server

```bash
python src/cli.py serve --debug
```

You should see:

```
* Running on http://127.0.0.1:8080
```

---

## ✅ Quick tests

Health check:

```bash
curl http://127.0.0.1:8080/api/health
```

Database ping (requires Mongo set up):

```bash
python src/cli.py db ping
```

---

## 🛠 CLI Commands

```bash
# Serve the web dashboard
python src/cli.py serve --debug

# Database operations
python src/cli.py db ping

# Data ingestion
python src/cli.py fetch-cloudflare --kind top --country GB --limit 50
python src/cli.py fetch-cloudflare --kind http --country GB --days 90
python src/cli.py fetch-cloudflare --kind l3 --country GB --days 90 --direction target
python src/cli.py fetch-cloudflare --kind bots --country GB --days 90

# OONI data
python src/cli.py fetch-ooni --country GB --days 180

# View configured events
python src/cli.py events

# Generate encryption keys
python src/cli.py secret gen-key
python src/cli.py secret gen-key --hmac
```

---

## 📊 Dashboard

Modern Flask web application with modular template structure:

**Template Architecture:**
- **Base Template** (`base.html`): Common HTML structure, CSS, and JavaScript libraries
- **Component Templates**: Modular, reusable components for each dashboard section
- **Main Dashboard** (`index.html`): Orchestrates all components using Flask template inheritance

**Dashboard Components:**
- **Header**: Title, description, current event display, API health link
- **Controls**: Country/date badges, refresh button
- **HTTP Chart**: Traffic volume analysis with 24h moving average
- **L3 Attacks**: Target and origin attack analysis (separate charts)
- **OONI Tor**: Tor reachability success rates
- **Bot Traffic**: Automated traffic percentage analysis
- **Top Domains**: Domain rankings with age-gate status
- **Age Gate**: Compliance tracking and daily counts
- **Data Insights**: Key metrics summary and quality assessment
- **Tor Metrics**: Bridge/relay visualization
- **Google Trends**: VPN search trends integration

**Features:**
- Responsive design with Tailwind CSS
- Interactive charts with Chart.js
- Real-time data loading from APIs
- Event-based time window analysis (30 days before/after)
- Age-gate compliance tracking for UK domains
- Google Trends integration with fallback

---

## 🧪 Testing

Run all tests:

```bash
pytest -q
```

---

## 📌 Recent Improvements

- **Template Refactoring**: Split monolithic `home.html` into modular, maintainable components
- **Improved Structure**: Clean separation between base template, components, and main dashboard
- **Better Organization**: Logical grouping of related functionality
- **Enhanced Maintainability**: Easy to modify individual components without affecting others
- **Modern Flask Patterns**: Proper use of template inheritance and includes
- **Data Flow Optimization**: Streamlined data ingestion and chart rendering pipeline
- **Time Window Management**: Charts now properly match available data ranges

---

## 📌 Roadmap

- [ ] Add control-country overlay (Diff-in-Diffs)
- [ ] Expand OONI ingest (Psiphon, Snowflake reliability)
- [ ] Optional: Google Trends bar Δ for multiple terms
- [ ] Auto-cron ingestion (scripts/bootstrap.sh)
- [ ] Component-level testing for template modules
- [ ] API documentation with OpenAPI/Swagger
- [ ] Real-time data streaming for live updates
- [ ] Advanced data caching and optimization

---

## 📜 License

MIT License. See [LICENSE](LICENSE).

## Technologies Used

### Backend Framework
- **Flask 3.x** - Modern Python web framework for building the API and web application
- **Flask-CORS** - Cross-Origin Resource Sharing support for API access

### Database
- **MongoDB** - NoSQL document database for storing time series data, domain rankings, and metrics
- **PyMongo** - Official MongoDB driver for Python with SRV connection support
- **MongoDB Atlas** - Cloud-hosted MongoDB service (configurable via environment variables)

### Data Processing & Analytics
- **Pandas** - Data manipulation and analysis library for processing time series data
- **NumPy** - Numerical computing library for mathematical operations and statistical analysis
- **PyTrends** - Unofficial Google Trends API wrapper for fetching search trend data

### Web Scraping & Automation
- **Pyppeteer** - Headless Chrome automation for taking screenshots of Google Trends pages
- **Requests** - HTTP library for making API calls to external services

### Security & Encryption
- **Cryptography** - Cryptographic recipes and primitives for data encryption
- **Fernet** - Symmetric encryption for sensitive data
- **HMAC** - Hash-based message authentication for data integrity

### Development & Testing
- **Pytest** - Testing framework for Python
- **Responses** - Mock library for testing HTTP requests
- **MongoMock** - MongoDB mocking for testing
- **FreezeGun** - Time freezing for deterministic testing

### Configuration & Environment
- **Python-dotenv** - Environment variable management from .env files

## Data Used

### Cloudflare Radar Data
- **HTTP Request Metrics** - Normalized HTTP request counts by country and time
- **Traffic Patterns** - Web traffic analysis and trends
- **Geographic Distribution** - Country-specific internet usage data
- **Bot Traffic** - Automated traffic detection and analysis

### OONI (Open Observatory of Network Interference) Data
- **Tor Reachability** - Daily Tor network accessibility metrics by country
- **Snowflake Proxy** - Censorship circumvention tool availability
- **Psiphon** - VPN tool reachability and performance
- **Measurement Data** - Network interference detection results

### Domain Ranking Data
- **Top Domains** - Country-specific domain popularity rankings
- **Traffic Volume** - Domain traffic metrics and trends
- **Category Classification** - Domain categorization (e.g., adult content, social media)

### Age Gate Verification Data
- **Curated Status** - Manually verified age verification requirements for major platforms
- **UK Compliance** - Age verification implementation status for UK regulations
- **Platform Analysis** - Social media, dating, and adult content platform compliance

### Google Trends Data
- **Search Patterns** - Search term popularity over time
- **Geographic Trends** - Country-specific search behavior
- **Temporal Analysis** - Search volume changes around specific events

### Event Registry
- **UK Age Verification (2025-07-25)** - Primary event tracking for regulatory changes
- **Tor Metrics Integration** - Tor Project metrics for relay and bridge usage
- **Country-Specific Events** - Regional internet policy changes and their impacts

## API Endpoints Created

### Health & System Status
- `GET /api/health` - System health check with database connectivity and configuration status
- `GET /api/debug-counts` - Collection document counts for data ingestion verification

### Time Series Data
- `GET /api/timeseries` - HTTP traffic metrics over time with optional control country comparisons
- `GET /api/window-stats` - Statistical analysis of traffic changes around specific events
- `GET /api/attacks` - Layer 3 attack metrics and DDoS data over time

### Domain Analysis
- `GET /api/top-domains` - Country-specific domain popularity rankings with optional category filtering
- `GET /api/top-domains/age-gated` - Top domains annotated with age verification status

### Age Gate Verification
- `GET /api/age-gate/status` - Current age verification status for major platforms
- `GET /api/age-gate/timeseries` - Daily count of age-gated domains in top rankings

### Network Interference (OONI)
- `GET /api/ooni/tor` - Tor network reachability data with global and country-specific views
- `GET /api/ooni/reachability` - Multi-tool reachability metrics (Tor, Snowflake, Psiphon)

### Search Trends
- `GET /api/trends/health` - Google Trends service availability check
- `GET /api/trends/png` - Screenshot generation of Google Trends pages to avoid rate limiting

### Event Management
- `GET /api/events` - List of configured events and their metadata
- `GET /api/event` - Individual event details by slug identifier

### Data Ingestion
- **Cloudflare Integration** - Automated ingestion of Radar metrics and traffic data
- **OONI Integration** - Scheduled collection of network interference measurements
- **MongoDB Indexing** - Automatic creation of database indexes for optimal query performance

### Query Parameters
All endpoints support flexible querying with:
- **Country Codes** - ISO country codes (e.g., GB, US, IE)
- **Date Ranges** - ISO date strings or relative day counts
- **Metrics** - Specific data types (http_requests_norm, l3_bps, bot_traffic)
- **Limits** - Result set size controls
- **Control Groups** - Comparative analysis with other countries

### Response Format
All API endpoints return consistent JSON responses with:
- `ok` - Boolean success indicator
- `time_utc` - ISO timestamp of response generation
- `country` - Requested country code
- `data` - Requested information in standardized format
- `error` - Error details when applicable
