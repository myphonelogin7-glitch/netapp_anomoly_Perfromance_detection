import pandas as pd
import numpy as np
import datetime
import uuid

# --- 1. AI Investigation Orchestrator ---
def run_investigation(vol_name, current_metrics, anomaly_severity, history_df=None):
    """
    Orchestrates the full AI investigation workflow.
    
    Args:
        vol_name (str): Name of the volume.
        current_metrics (dict): Dictionary containing 'Latency_ms', 'IOPS', 'Throughput_MB'.
        anomaly_severity (str): 'High', 'Medium', or 'Low'.
        history_df (pd.DataFrame): Historical data for the volume (optional, for graphing).
        
    Returns:
        dict: The complete Investigation Result Object.
    """
    
    # Initialize Investigation ID
    inv_id = f"INV-{datetime.datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
    
    # 1. Anomaly Confirmation
    # (In a real system, we'd fetch history again here, but for POC we trust the input severity)
    confirmation = confirm_anomaly(current_metrics, anomaly_severity)
    
    if not confirmation['confirmed']:
        return {
            "id": inv_id,
            "status": "Dismissed",
            "reason": "Anomaly not statistically significant."
        }
        
    # 2. Behavioral Correlation (The "Brain")
    behavior_analysis = analyze_behavior(current_metrics)
    
    # 3. Root Cause Analysis
    rca = determine_root_cause(behavior_analysis)
    
    # 4. Recommendations
    actions = generate_recommendations(rca['primary_cause'])
    
    # 5. Build Result Object
    result = {
        "id": inv_id,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "volume": vol_name,
        "status": "Completed",
        "severity": anomaly_severity,
        "metrics": current_metrics,
        "history": history_df,  # Store for reporting
        "analysis": {
            "behavior_pattern": behavior_analysis['pattern'],
            "description": behavior_analysis['description'],
            "metrics_correlation": behavior_analysis['correlation_text']
        },
        "findings": {
            "primary_cause": rca['primary_cause'],
            "confidence_score": rca['confidence'],
            "reasoning": rca['reasoning']
        },
        "recommendations": actions
    }
    
    return result

# --- 2. Anomaly Confirmation Engine ---
def confirm_anomaly(metrics, severity):
    """
    Validates if the anomaly is worth investigating.
    """
    # POC Logic: If it's High severity, we always investigate.
    # In prod, this would check against specific Baseline objects.
    if severity == "High" or metrics['Latency_ms'] > 10.0:
        return {"confirmed": True}
    return {"confirmed": False}

# --- 3. Behavioral Correlation Engine (Explainable AI) ---
def analyze_behavior(metrics):
    """
    Correlates Latency, IOPS, and Throughput to identify the BEHAVIOR pattern.
    Rules:
    - High Latency + Dropping IOPS = Backend Stall (System can't process)
    - High Latency + High IOPS = Workload Surge (System saturated by demand)
    - High Latency + Normal IOPS = Contention/Locking (Waiting on something)
    """
    lat = metrics.get('Latency_ms', 0)
    iops = metrics.get('IOPS', 0)
    tput = metrics.get('Throughput_MB', 0)
    
    # Heuristic Thresholds (POC)
    # Ideally these come from the Baseline object
    HIGH_LATENCY = 10.0
    HIGH_IOPS = 3000.0  # Assumed generic baseline
    LOW_IOPS = 800.0
    
    pattern = "Unknown"
    description = "Unusual activity detected."
    correlation = ""
    
    if lat > HIGH_LATENCY:
        if iops > HIGH_IOPS:
            pattern = "Workload Surge"
            description = "The volume is pushing more IOPS and Throughput than its historical baseline, initiating latency."
            correlation = "POSITIVE CORRELATION: Latency is rising in step with increased IOPS demand."
        elif iops < LOW_IOPS:
            pattern = "Backend Stall"
            description = "Latency is high despite low or dropping IOPS. The storage backend is struggling to serve requests."
            correlation = "NEGATIVE CORRELATION: Latency is rising while IOPS are falling/stalled."
        else:
            pattern = "Resource Contention"
            description = "Latency is elevated while throughput and IOPS remain normal. This suggests external contention (Noisy Neighbor) or internal locks."
            correlation = "DECOUPLED: Latency is independent of current volume load."
            
    return {
        "pattern": pattern,
        "description": description,
        "correlation_text": correlation
    }

# --- 4. Root Cause Hypothesis Engine ---
def determine_root_cause(behavior):
    """
    Maps behavior patterns to probable root causes with confidence scores.
    """
    pattern = behavior['pattern']
    
    if pattern == "Workload Surge":
        return {
            "primary_cause": "Application Demand Spike",
            "confidence": "92%",
            "reasoning": "The correlation between high IOPS and high Latency is strong/linear."
        }
    elif pattern == "Backend Stall":
        return {
            "primary_cause": "Disk/Aggregate Subsystem Latency",
            "confidence": "88%",
            "reasoning": "Inverse relationship (High Latency / Low IOPS) indicates the bottleneck is internal to the storage system (disk or CPU saturation)."
        }
    elif pattern == "Resource Contention":
        return {
            "primary_cause": "QoS Throttling or Noisy Neighbor",
            "confidence": "75%",
            "reasoning": "Volume load is normal, identifying the constraint as external (shared resource contention)."
        }
    
    return {
        "primary_cause": "Transient Anomaly",
        "confidence": "50%",
        "reasoning": "Data pattern matches no known failure modes."
    }

# --- 5. Recommendation Engine ---
def generate_recommendations(cause):
    """
    Returns a list of SAFE, advisory actions based on the root cause.
    """
    if cause == "Application Demand Spike":
        return [
            "Validate if this is a scheduled batch job or backup.",
            "Review QoS Max limits to ensure they aren't capping valid burst traffic.",
            "Consider moving volume to a higher-performance aggregate if trend persists."
        ]
    elif cause == "Disk/Aggregate Subsystem Latency":
        return [
            "Check Aggregate Utilization (is it > 90%?).",
            "Verify status of background jobs (Disk Reconstruction, Deduplication).",
            "Investigate physical disk health in the underlying aggregate."
        ]
    elif cause == "QoS Throttling or Noisy Neighbor":
        return [
            "Check for other high-traffic volumes on the same aggregate.",
            "Review QoS Min/Max settings for this volume.",
            "Analyze 'Top Hogs' report for the cluster."
        ]
        
    return ["Monitor situation for recurrence.", "Check system logs for errors."]
