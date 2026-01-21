import pandas as pd
import numpy as np

def load_data(file_path):
    """
    Loads storage data from CSV.
    EXPECTS: Volume_Name, Timestamp, Latency_ms
    """
    df = pd.read_csv(file_path)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df['Hour'] = df['Timestamp'].dt.hour
    return df

def calculate_baseline(df):
    """
    Calculates the 'normal' behavior (Mean, StdDev) per Volume and Hour.
    """
    # Group by Volume and Hour
    baseline = df.groupby(['Volume_Name', 'Hour'])['Latency_ms'].agg(['mean', 'std']).reset_index()
    baseline.rename(columns={'mean': 'Baseline_Mean', 'std': 'Baseline_Std'}, inplace=True)
    # Handle cases with 0 std (single data point or constant), replace with small epsilon
    baseline['Baseline_Std'] = baseline['Baseline_Std'].replace(0, 0.1)
    return baseline

def detect_anomalies(df, std_threshold=3.0):
    """
    Detects anomalies by comparing actual latency to the baseline.
    Anomaly = Latency > Mean + (std_threshold * StdDev)
    Returns original DF with added columns: Baseline_Mean, Baseline_Std, Upper_Bound, Is_Anomaly, Severity
    """
    # Calculate baseline
    baseline = calculate_baseline(df)
    
    # Merge baseline back to original data
    merged = pd.merge(df, baseline, on=['Volume_Name', 'Hour'], how='left')
    
    # Calculate Upper Bound
    merged['Upper_Bound'] = merged['Baseline_Mean'] + (std_threshold * merged['Baseline_Std'])
    merged['Lower_Bound'] = merged['Baseline_Mean'] - (std_threshold * merged['Baseline_Std'])
    # Latency shouldn't really be below 0, but for completeness (and avoiding clutter) we focus on high latency
    merged['Lower_Bound'] = merged['Lower_Bound'].clip(lower=0) 

    # Flag Anomalies (High Latency)
    merged['Is_Anomaly'] = merged['Latency_ms'] > merged['Upper_Bound']
    
    # Determine Severity
    # Low: > 3 std, Med: > 5 std, High: > 8 std
    conditions = [
        merged['Latency_ms'] > (merged['Baseline_Mean'] + 8 * merged['Baseline_Std']),
        merged['Latency_ms'] > (merged['Baseline_Mean'] + 5 * merged['Baseline_Std']),
        merged['Latency_ms'] > merged['Upper_Bound']
    ]
    choices = ['High', 'Medium', 'Low']
    merged['Severity'] = np.select(conditions, choices, default='Normal')
    
    # Root Cause Hints
    rc_conditions = [
        merged['Severity'] == 'High',
        merged['Severity'] == 'Medium',
        merged['Severity'] == 'Low'
    ]
    rc_choices = [
        'Possible Backend Contention', 
        'Potential Workload Spike', 
        'Transient I/O Burst'
    ]
    merged['Root_Cause'] = np.select(rc_conditions, rc_choices, default='None')
    
    # Troubleshooting Recommendations
    res_conditions = [
        merged['Root_Cause'] == 'Possible Backend Contention',
        merged['Root_Cause'] == 'Potential Workload Spike',
        merged['Root_Cause'] == 'Transient I/O Burst'
    ]
    res_choices = [
        'Check aggregate utilization and disk saturation.',
        'Identify top consumers and review QoS policies.',
        'Monitor for recurrence; no immediate action.'
    ]
    merged['Resolution_Steps'] = np.select(res_conditions, res_choices, default='N/A')
    
    return merged

if __name__ == "__main__":
    # Test run
    try:
        print("Testing anomaly detection...")
        df = load_data('storage_data.csv')
        processed = detect_anomalies(df)
        
        anomalies = processed[processed['Is_Anomaly'] == True]
        print(f"Total Rows: {len(processed)}")
        print(f"Total Anomalies Detected: {len(anomalies)}")
        print(f"Sample Anomalies:\n{anomalies[['Timestamp', 'Volume_Name', 'Latency_ms', 'Upper_Bound', 'Severity']].head()}")
        
    except Exception as e:
        print(f"Error: {e}")
