# 🧬 DaVita - AI-Powered Data Intelligence Platform

<div align="center">

![DaVita Banner](https://img.shields.io/badge/DaVita-AI%20Powered-purple?style=for-the-badge&logo=chartdotjs)
[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![AI](https://img.shields.io/badge/Google-Gemini-yellow?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)

**Transform CSV data into actionable insights with AI-driven correlation analysis and intelligent null-value handling**

</div>

---

## ✨ What Makes DaVita Special?

DaVita is not just another data visualization tool. It's an **AI-powered data intelligence platform** that understands your data, explains it in natural language, and makes smart decisions about data quality.

### 🤖 AI-Style, But Fully Local (Free)

- **Local “AI” Explanations** - Human‑readable summaries generated directly from your data (no API)
- **Heuristic Recommendations** - Built‑in logic suggests null-value handling strategies
- **Correlation Detection** - Automatically identifies relationships between variables
- **Natural Language‑Style Insights** - Understand your data through structured summaries
- **Smart Imputation** - Correlation-aware null handling without any external service

### 🔧 Advanced Data Processing

- **Correlation-Aware Null Handling** - Maintains statistical relationships during imputation
- **7 Imputation Strategies** - Auto, mean, median, mode, forward fill, backward fill, or drop
- **Real-Time Quality Assessment** - Live analysis of missing values and data quality
- **Automated Strategy Selection** - AI picks the best method for your specific dataset

### 📊 Beautiful Visualizations

- **15+ Chart Types** - Heatmaps, scatter plots, distributions, KDE, violin plots, and more
- **Modern Glassmorphism UI** - Purple/violet gradient theme with particle effects
- **Heavy Animations** - Floating orbs, gradient shifts, twinkling stars
- **Fully Responsive** - Gorgeous on desktop and mobile devices

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Internet browser (Chrome, Edge, Firefox, etc.)

### Installation (Local App for Anyone)

1. **Download or copy the project folder** to any machine.

2. **Open a terminal in the project folder** (where `main.py` and `requirements.txt` live):
   ```bash
   cd DataVisualization_CSVanalyzer-main
   ```

3. **(Optional but recommended) Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**:
   ```bash
   python main.py
   ```

6. **Open in browser**:
   ```
   http://127.0.0.1:5000
   ```

---

## 📱 Mobile Access

### Local Network
1. Find your PC's IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
2. On mobile: `http://YOUR_PC_IP:5000`

### Deploy Online (Free Options)

You can still deploy as a standard Flask app to services like Render / Railway / PythonAnywhere
using `render.yaml` / `railway.json`. No API keys are required anymore; just deploy the app and
access it via the generated URL.

---

## 💡 How to Use

1. **Upload CSV File** - Max 16MB, drag & drop supported
2. **Get AI Recommendations** (optional) - See AI suggestions for handling nulls
3. **Select Strategy** - Choose or let AI pick the best null-value handling method
4. **Analyze Data** - Watch AI generate insights and visualizations
5. **Explore Results** - View charts, correlations, and AI explanations

---

## 🎨 Tech Stack

### Backend
- **Flask 3.0** - Web framework
- **Python 3.13** - Programming language
- **Pandas** - Data manipulation
- **NumPy** - Numerical computing

### AI & ML
- **Local Heuristics** - AI-style analysis and explanations without external APIs
- **Correlation Analysis** - Statistical relationship detection
- **Smart Imputation** - Intelligent null-value handling

### Visualization
- **Matplotlib 3.8** - Core plotting library
- **Seaborn 0.13** - Statistical visualizations

### Frontend
- **HTML5 & CSS3** - Modern web standards
- **Vanilla JavaScript** - No framework dependencies
- **Glassmorphism Design** - Frosted glass effect
- **Particle Effects** - Floating orbs and stars

---

## 📂 Project Structure

```
DaVita/
├── main.py                 # Flask app & AI logic
├── templates/
│   └── index.html         # Frontend UI with glassmorphism
├── static/
│   └── outputs/           # Generated visualizations
├── requirements.txt       # Python dependencies
├── .env                   # API configuration (git ignored)
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

---

## 🔒 Security & Privacy

- ✅ **API Keys Protected** - `.env` file never committed to git
- ✅ **Input Validation** - CSV files validated before processing
- ✅ **Size Limits** - 16MB maximum upload size
- ✅ **Secure Handling** - No data stored permanently
- ✅ **Environment Variables** - Sensitive data kept separate

---

## 🛠️ Null Handling Strategies

| Strategy | Best For | How It Works |
|----------|----------|--------------|
| **Auto** | Unknown data | AI analyzes correlations and picks optimal method |
| **Mean** | Normally distributed | Fill numeric with mean, categorical with mode |
| **Median** | Skewed distributions | Fill numeric with median, categorical with mode |
| **Mode** | Categorical-heavy | Fill all columns with most frequent value |
| **Forward Fill** | Time series | Propagate last valid value forward |
| **Backward Fill** | Time series | Propagate next valid value backward |
| **Drop Rows** | High data quality | Remove rows with any missing values |

---

## 📊 Visualization Gallery

### Statistical Plots
- Correlation Heatmap
- Distribution Histogram with KDE
- Box Plot (Outlier Detection)
- Violin Plot
- KDE Plot (1D & 2D)
- Box Plot with Swarm

### Relationship Plots
- Scatter Plot with Color Mapping
- Line Plot
- Area Plot
- 3D Scatter Plot

### Categorical Plots
- Bar Chart with Annotations
- Count Plot
- Strip Plot

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. **Fork** the repository
2. **Create** feature branch: `git checkout -b feature/AmazingFeature`
3. **Commit** changes: `git commit -m 'Add AmazingFeature'`
4. **Push** to branch: `git push origin feature/AmazingFeature`
5. **Open** a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Add docstrings to new functions
- Test with multiple CSV datasets
- Update README if adding features

---

## 📝 Copyright & License

**Copyright (c) 2026 Mahir. All Rights Reserved.**

DaVita is a derivative work with substantial original contributions including:
- ✨ AI-powered correlation analysis using Google Gemini
- ✨ Intelligent null-value handling with correlation preservation
- ✨ Complete UI/UX redesign with glassmorphism theme
- ✨ Advanced particle effects and animations
- ✨ AI explanation and recommendation system
- ✨ DaVita branding and identity

*Original base structure: DataViz CSV Analyzer*

The enhancements and AI features are the intellectual property of Mahir.

---

## 🙏 Acknowledgments

- **Base Structure** - DataViz CSV Analyzer by [Amir Sakib Saad](https://github.com/amirsakib16)
- **AI Engine** - Google Gemini by Google AI
- **Visualization Libraries** - Matplotlib & Seaborn teams
- **Web Framework** - Flask community
- **Design Inspiration** - Modern glassmorphism aesthetic

---

## 📧 Contact & Support

**Mahir** - Creator & Maintainer

- 🐙 GitHub: [@YOUR_USERNAME](https://github.com/YOUR_USERNAME)
- 📦 Repository: [DaVita](https://github.com/YOUR_USERNAME/DaVita)

### Get Help
- 🐛 **Found a bug?** Open an issue
- 💡 **Have an idea?** Start a discussion
- ❓ **Need help?** Check existing issues or create new one

---

## 🎯 Roadmap

### Version 2.0 (Coming Soon)
- [ ] Real-time collaborative analysis
- [ ] Excel & JSON file support
- [ ] Export reports to PDF
- [ ] Custom visualization templates
- [ ] Enhanced AI insights with GPT-4

### Version 2.1
- [ ] Dashboard builder
- [ ] Scheduled analysis
- [ ] API for programmatic access
- [ ] Multi-language support
- [ ] Dark mode toggle

### Version 3.0
- [ ] Machine learning predictions
- [ ] Automated reporting
- [ ] Team collaboration features
- [ ] Cloud storage integration

---

<div align="center">

**Built with ❤️ using Python, Flask, and AI**

*Transform Data Into Intelligence*

![Made with Python](https://img.shields.io/badge/Made%20with-Python-blue?style=flat-square&logo=python)
![Powered by AI](https://img.shields.io/badge/Powered%20by-AI-purple?style=flat-square&logo=google)
![Modern UI](https://img.shields.io/badge/Modern-UI%2FUX-pink?style=flat-square)

</div>
