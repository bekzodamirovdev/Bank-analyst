# 🏦 Bank AI Data Analyst

**AI-powered Data Analysis Tool for Banking Systems**

Natural language query processing system using Local LLM (Llama 3.2) for SQL generation, data analysis, and automated Excel reporting.

## 🌟 Features

- ✅ **1M+ Records Mock Database** - Clients, Accounts, Transactions
- ✅ **Local LLM Integration** - Ollama + Llama 3.2
- ✅ **Natural Language → SQL** - Uzbek/English query support
- ✅ **Excel Export with Charts** - Bar, Pie, Line charts
- ✅ **Modern Web UI** - Clean, responsive interface
- ✅ **CLI Support** - Terminal-based operations
- ✅ **Docker Ready** - Containerized deployment

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Ollama ([Download](https://ollama.com/download))
- SQLite3

### Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/bank-ai-analyst.git
cd bank-ai-analyst

# Create virtual environment
python3 -m venv env
source env/bin/activate  # Windows: env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install & start Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull llama3.2

# Setup database (generates 1M+ records)
python bank_analyst.py --setup
```

### Run

```bash
# Start backend server
python web_app.py

# Open browser
http://localhost:5000
```

## 📊 Usage Examples

### CLI

```bash
# Natural language query
python bank_analyst.py --query "Show number of clients by region"

# Generate Excel report
python bank_analyst.py --query "Top 10 accounts by balance" --chart bar
```

### Web UI

1. Open `http://localhost:5000`
2. Enter query: "Toshkent viloyatidagi mijozlar sonini ko'rsat"
3. Click "Tahlil qilish" for results or "Excel hisobot" for report

### API

```bash
# Get statistics
curl http://localhost:5000/api/stats

# Execute query
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT COUNT(*) FROM clients", "chart_type": "bar"}'
```

## 📁 Project Structure

```
bank-ai-analyst/
├── bank_analyst.py          # Core AI assistant & database logic
├── web_app.py              # Flask API backend
├── index.html              # Frontend UI
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose setup
├── demo.sh               # Demo script
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## 🗄️ Database Schema

### Tables

| Table | Records | Description |
|-------|---------|-------------|
| **clients** | 50,000 | Customer information |
| **accounts** | ~75,000 | Bank accounts |
| **transactions** | 1M+ | Transaction history |

### Regions

Toshkent, Samarqand, Buxoro, Andijon, Farg'ona, Namangan, Qashqadaryo, Surxondaryo, Jizzax, Sirdaryo, Navoiy, Xorazm, Qoraqalpog'iston

## 🐳 Docker

```bash
# Build image
docker build -t bank-analyst .

# Run container
docker run -p 5000:5000 -p 11434:11434 bank-analyst

# Or use Docker Compose
docker-compose up -d
```

## 🔧 Configuration

### Environment Variables

```bash
FLASK_ENV=production
DATABASE_PATH=bank_data.db
LLM_MODEL=llama3.2
LLM_URL=http://localhost:11434
```

## 📚 API Documentation

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Database statistics |
| POST | `/api/query` | Execute query |
| POST | `/api/generate_report` | Generate Excel |
| GET | `/download/<file>` | Download Excel |
| GET | `/api/examples` | Query examples |
| GET | `/health` | Health check |

## 🧪 Testing

```bash
# Run validation tests
python final_validation.py

# Quick test
python bank_analyst.py --query "SELECT COUNT(*) FROM clients"
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.com) - Local LLM runtime
- [Llama 3.2](https://ai.meta.com/llama/) - Meta's language model
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [OpenPyXL](https://openpyxl.readthedocs.io/) - Excel library

## 📧 Contact

Your Name - [@yourtwitter](https://twitter.com/yourtwitter)

Project Link: [https://github.com/YOUR_USERNAME/bank-ai-analyst](https://github.com/YOUR_USERNAME/bank-ai-analyst)

## 🎯 Features Roadmap

- [ ] Multi-language support (English, Russian)
- [ ] PostgreSQL/MySQL support
- [ ] Advanced data visualizations
- [ ] User authentication
- [ ] Query history
- [ ] Scheduled reports

---

**Made with ❤️ for AI Developer Test Assignment**