# FIFA-Player-Position-Prediction

## Overview
This project predicts a soccer player's position (**Forward, Midfielder, or Defender**) using machine learning techniques.  
The model is trained on **FIFA datasets from FIFA 15 to FIFA 23**, leveraging player attributes such as physical, technical, and mental characteristics.

The system includes:
- A **Flask-based web application** for real-time predictions
- An **Android UI** for mobile-based interaction

---

## Features

### Big Data Processing
- Uses **PySpark** to efficiently process large FIFA datasets.

### Machine Learning Model
- Implements a **Random Forest Classifier**
- Includes feature engineering and class balancing techniques.

### Web-Based Deployment
- Flask web app for real-time player position prediction.

### Android Integration
- Android UI enables predictions directly from mobile devices via Flask API.

---

## Technologies Used

### Machine Learning
- Python
- PySpark
- Random Forest Classifier (Scikit-learn)

### Backend
- Flask

### Frontend
- Android (Java/Kotlin)
- HTML/CSS (Web UI)


---

## Dataset

**Source:** FIFA 15 – FIFA 23 datasets  

### Key Features Used
- **Physical:** Pace, Strength, Stamina  
- **Technical:** Passing, Shooting, Dribbling  
- **Mental:** Vision, Composure, Positioning  
- **Defensive:** Tackling, Marking  

---

## Installation & Setup

### 1. Web Application

#### Prerequisites
- Python 3.7+
- Flask
- PySpark

#### Steps
```bash
pip install flask pyspark scikit-learn pandas
python app.py
