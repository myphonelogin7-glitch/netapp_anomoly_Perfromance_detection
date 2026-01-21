import pandas as pd
import numpy as np
import datetime
import random

def generate_synthetic_data(file_path='storage_data.csv', num_days=30):
    """
    Generates synthetic storage latency data for a fictional NetApp environment.
    """
    print(f"Generating data for {num_days} days...")
    
    # Configuration
    # Configuration (Must match app.py mock_fleet names)
    volumes = [
        'AZURETEST', 'DESKTOPS', 'mysql_db', 'mysql_logs', 
        'ORCLA_root', 'sql3sb_root', 'sql_db', 'sql_logs',
        'vol_vdi_boot', 'vol_analytics_01'
    ]
    start_time = datetime.datetime.now() - datetime.timedelta(days=num_days)
    end_time = datetime.datetime.now()
    freq = '5min'
    
    # Generate Time Series
    timestamps = pd.date_range(start=start_time, end=end_time, freq=freq)
    
    all_data = []

    for vol in volumes:
        # Base latency logic:
        # 1. Sinusoidal pattern (higher during day, lower at night)
        # 2. Random Gaussian noise
        # 3. Different characteristics per volume
        
        base_latency = random.uniform(2.0, 5.0) # Base ms
        vol_noise_factor = random.uniform(0.5, 1.5)
        
        # Create a day-of-week factor (weekends quieter?)
        # For simplicity, just daily cycle here.
        
        # Vectorized generation for speed
        n = len(timestamps)
        
        # Hour of day component (0-23 converted to radians for sine)
        hours = timestamps.hour.values + timestamps.minute.values / 60.0
        daily_pattern = np.sin((hours - 6) * np.pi / 12) # Peak around 12 PM (noon)
        # Shift sine to be 0 to 1-ish
        daily_pattern = (daily_pattern + 1) / 2 # Normalize 0-1
        
        # Latency series
        # Base + (Pattern * Amplitude) + Noise
        latency_series = base_latency + (daily_pattern * 5.0) + np.random.normal(0, vol_noise_factor, n)
        
        # Ensure no negative latency
        latency_series = np.maximum(latency_series, 0.5)
        
        # 4. Generate IOPS (Poisson-like but scaled) - correlated with latency slightly
        # Base load + daily cycle + random noise
        base_iops_vol_factor = random.uniform(500, 2000) # Base IOPS for this volume
        iops_series = base_iops_vol_factor + (daily_pattern * 1000) + np.random.normal(0, 200, n)
        iops_series = np.maximum(iops_series, 0) # Ensure no negative IOPS

        # 5. Generate Throughput (MB/s) -> IOPS * BlockSize (random between 4k and 64k mixed)
        # roughly: IOPS * (avg 32KB) / 1024 / 1024
        avg_block_size_kb = np.random.normal(32, 10, n)
        avg_block_size_kb = np.maximum(avg_block_size_kb, 4) # min 4KB
        throughput_series = (iops_series * avg_block_size_kb) / 1024
        throughput_series = np.maximum(throughput_series, 0) # Ensure no negative throughput

        # Inject Anomalies (Spikes)
        # 1% chance of a spike
        num_anomalies = int(n * 0.01)
        anomaly_indices = np.random.choice(n, num_anomalies, replace=False)
        
        # Latency spikes
        latency_series[anomaly_indices] += np.random.uniform(20.0, 100.0, num_anomalies)
        # IOPS spikes (often correlated with latency spikes, but can be independent)
        iops_series[anomaly_indices] += np.random.uniform(2000, 5000, num_anomalies)
        # Throughput spikes (derived from IOPS spikes)
        throughput_series[anomaly_indices] = (iops_series[anomaly_indices] * avg_block_size_kb[anomaly_indices]) / 1024
        
        # Inject Sustained High Latency (e.g., a "storm" lasting 1 hour)
        # Pick 2 random start points
        for _ in range(2):
            start_idx = random.randint(0, n - 24) # 24 5-min intervals = 2 hours approx
            duration = random.randint(6, 24) 
            
            # Latency storm
            latency_series[start_idx : start_idx + duration] += random.uniform(15.0, 40.0)
            # IOPS might drop or stay high during a latency storm, let's make it drop slightly
            iops_series[start_idx : start_idx + duration] = np.maximum(iops_series[start_idx : start_idx + duration] * random.uniform(0.5, 0.8), 0)
            # Throughput adjusted based on new IOPS
            throughput_series[start_idx : start_idx + duration] = (iops_series[start_idx : start_idx + duration] * avg_block_size_kb[start_idx : start_idx + duration]) / 1024


        # Build DataFrame part
        df_vol = pd.DataFrame({
            'Volume_Name': vol,
            'Timestamp': timestamps,
            'Latency_ms': latency_series,
            'IOPS': iops_series,
            'Throughput_MB': throughput_series
        })
        all_data.append(df_vol)
    
    # Combine all
    final_df = pd.concat(all_data)
    
    # Sort
    final_df.sort_values(by=['Volume_Name', 'Timestamp'], inplace=True)
    
    # Round latency for readability
    final_df['Latency_ms'] = final_df['Latency_ms'].round(2)
    
    # Save
    final_df.to_csv(file_path, index=False)
    print(f"Successfully generated {len(final_df)} rows of data at {file_path}")

def inject_latency_spike(vol_name, scenario="random", duration_mins=30):
    """
    Injects a real-time latency spike based on realistic, baseline-relative scenarios.
    Defaults to 30 mins to simulate a CURRENT incident onset.
    """
    try:
        df = pd.read_csv('storage_data.csv')
        
        # 1. Get Robust Baseline (Median of last 50 points to avoid outlier compounding)
        vol_data = df[df['Volume_Name'] == vol_name]
        if not vol_data.empty:
            # Look at recent history (last 50 points ~ 4 hours)
            recent_history = vol_data.tail(50)
            base_lat = recent_history['Latency_ms'].median()
            base_iops = recent_history['IOPS'].median()
            base_tput = recent_history['Throughput_MB'].median()
            
            # Safety: If median is 0 or NaN (shouldn't happen), fall back
            if pd.isna(base_lat) or base_lat < 1: base_lat = 2.0
            if pd.isna(base_iops) or base_iops < 100: base_iops = 1000.0
            if pd.isna(base_tput) or base_tput < 5: base_tput = 50.0
        else:
            # Fallback defaults
            base_lat = 2.0
            base_iops = 1000.0
            base_tput = 50.0

        # 2. Select Scenario (Weighted Probabilities)
        if scenario == "random":
            # 40% Latency Contention (Latency up, IOPS slight jitter)
            # 40% Workload Burst (IOPS up, Latency up)
            # 20% Backend Stall (Latency HUGE, IOPS down)
            choices = ["contention", "burst", "stall"]
            weights = [0.4, 0.4, 0.2] 
            scenario = random.choices(choices, weights=weights, k=1)[0]
            
        print(f"Injecting scenario: {scenario} (Base Lat:{base_lat:.2f}, IOPS:{base_iops:.0f})")
        
        # Use CURRENT time
        # NEW LOGIC: Random duration between 5 and 15 minutes
        # Start time should be (Now - Duration) so it ENDS at 'Now'
        actual_duration_mins = random.randint(5, 15)
        print(f"Randomized Duration: {actual_duration_mins} mins")
        
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(minutes=actual_duration_mins)
        
        # Generate timestamps from start_time to end_time (inclusive)
        steps = int(actual_duration_mins / 5) + 1
        new_times = [start_time + datetime.timedelta(minutes=5 * i) for i in range(steps)]
        
        new_rows = []
        for t in new_times:
            # Add organic variance
            jitter_iops = random.uniform(0.9, 1.1)
            jitter_tput = random.uniform(0.9, 1.1)
            
            if scenario == "contention": 
                # "Noisy Neighbor" - Latency jumps significantly
                # IOPS/Tput shouldn't be perfectly flat - they suffer slightly or jitter
                lat = max(15.0, base_lat * random.uniform(4, 8)) 
                iops = base_iops * random.uniform(0.8, 1.1) # Erratic IOPS
                tput = base_tput * random.uniform(0.8, 1.1)
                
            elif scenario == "burst":
                # "Morning Boot Storm" - IOPS/Tput surge
                factor = random.uniform(2.5, 4.0) 
                iops = base_iops * factor
                tput = base_tput * factor
                # Latency increases with load, but not linearly
                lat = max(base_lat * 2, base_lat + (factor * 2)) 
                
            elif scenario == "stall":
                # "Disk Failure" - Latency explodes, IOPS decreases
                lat = max(80.0, base_lat * 15)
                iops = base_iops * random.uniform(0.3, 0.6) # Significant drop
                tput = base_tput * random.uniform(0.3, 0.6)
            
            else:
                lat, iops, tput = 50, 1000, 50

            new_rows.append({
                'Volume_Name': vol_name,
                'Timestamp': t,
                'Latency_ms': round(lat, 2),
                'IOPS': round(iops, 0),
                'Throughput_MB': round(tput, 2)
            })
            
        spike_df = pd.DataFrame(new_rows)
        spike_df.to_csv('storage_data.csv', mode='a', header=False, index=False)
        return True
    except Exception as e:
        print(f"Injection failed: {e}")
        return False

def inject_normal_data(vol_name, duration_mins=15):
    """
    Injects normal data AND removes any future 'bad' data to effectively stop the simulation.
    """
    try:
        df = pd.read_csv('storage_data.csv')
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        
        current_time = datetime.datetime.now()
        
        # 1. REMOVE FUTURE DATA for this volume (The sustained spike we just added)
        # Keep data that is NOT (This Volume AND in the Future)
        mask = ~((df['Volume_Name'] == vol_name) & (df['Timestamp'] > current_time))
        df_clean = df[mask].copy() # Work on a copy
        
        # 2. RETROACTIVE CLEANUP: Clear spikes from the last 60 minutes
        # Find rows for this volume in the last hour and reset their values to normal
        one_hour_ago = current_time - datetime.timedelta(hours=1)
        retro_mask = (df_clean['Volume_Name'] == vol_name) & \
                     (df_clean['Timestamp'] >= one_hour_ago) & \
                     (df_clean['Timestamp'] <= current_time)
                     
        if retro_mask.any():
            print(f"Cleaning {retro_mask.sum()} historical rows for {vol_name}...")
            # Set to normal baselines directly
            df_clean.loc[retro_mask, 'Latency_ms'] = df_clean.loc[retro_mask, 'Latency_ms'].apply(lambda x: random.uniform(1.0, 3.0))
            df_clean.loc[retro_mask, 'IOPS'] = df_clean.loc[retro_mask, 'IOPS'].apply(lambda x: random.uniform(800, 1200))
            df_clean.loc[retro_mask, 'Throughput_MB'] = df_clean.loc[retro_mask, 'Throughput_MB'].apply(lambda x: random.uniform(30, 50))
        
        # 2. Append ONE clean data point explicitly at NOW to bridge the gap
        # And a few minutes into future to show "All Green"
        new_times = [current_time + datetime.timedelta(minutes=5 * i) for i in range(int(duration_mins/5) + 1)]
        
        new_rows = []
        for t in new_times:
            new_rows.append({
                'Volume_Name': vol_name,
                'Timestamp': t,
                'Latency_ms': random.uniform(1.0, 3.0),   # Very Healthy
                'IOPS': random.uniform(800, 1200),        # Normal
                'Throughput_MB': random.uniform(30, 50)   # Normal
            })
            
        norm_df = pd.DataFrame(new_rows)
        
        # Combine clean history + new normal future
        final_df = pd.concat([df_clean, norm_df], ignore_index=True)
        final_df.sort_values(by=['Volume_Name', 'Timestamp'], inplace=True)
        
        final_df.to_csv('storage_data.csv', index=False)
        print(f"Normalized {vol_name} and cleaned future data.")
        return True
    except Exception as e:
        print(f"Normalization failed: {e}")
        return False

if __name__ == "__main__":
    generate_synthetic_data()
