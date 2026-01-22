from fpdf import FPDF
import pandas as pd
import datetime
import os

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'ONTAP Anomaly Report', 0, 0, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

def generate_pdf_report(anomalies_df, filename="anomaly_report.pdf"):
    """
    Generates a PDF report for the detected anomalies.
    """
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    
    # Title & Timestamp
    pdf.cell(0, 10, f'Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1)
    pdf.ln(5)
    
    if anomalies_df.empty:
        pdf.cell(0, 10, 'No anomalies detected currently.', 0, 1)
    else:
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 10, f"Total Critical Events: {len(anomalies_df)}", 0, 1, fill=True)
        pdf.ln(10)
        
        # Table Header
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(40, 10, 'Volume', 1)
        pdf.cell(45, 10, 'Time', 1)
        pdf.cell(25, 10, 'Latency', 1)
        pdf.cell(30, 10, 'Severity', 1)
        pdf.cell(50, 10, 'Root Cause', 1)
        pdf.ln()
        
        # Table Rows
        pdf.set_font('Arial', '', 9)
        for _, row in anomalies_df.iterrows():
            pdf.cell(40, 10, str(row['Volume_Name']), 1)
            pdf.cell(45, 10, str(row['Timestamp']), 1)
            pdf.cell(25, 10, f"{row['Latency_ms']} ms", 1)
            pdf.cell(30, 10, str(row['Severity']), 1)
            pdf.cell(50, 10, str(row['Root_Cause']), 1)
            pdf.ln()
            
    pdf.output(filename, 'F')
    return filename

def generate_investigation_report(investigation_result, filename="investigation_report.pdf"):
    """
    Generates a detailed, manager-friendly PDF report from an AI investigation result.
    """
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # --- Header ---
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'AI Storage Performance Investigation', 0, 1, 'C')
    pdf.ln(5)
    
    # --- Incident Summary Box ---
    # Draw box dynamically below the title
    box_y = pdf.get_y()
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, box_y, 190, 48, 'F') # Increased height for 4 rows
    
    # Position text inside the box
    pdf.set_y(box_y + 5)
    
    # Calculate dynamic timing if history is present
    start_str = "N/A"
    end_str = "N/A"
    dur_str = "Unknown"
    
    if 'history' in investigation_result and not investigation_result['history'].empty:
        hist = investigation_result['history']
        # Ensure regex or format doesn't break if already datetime
        if not pd.api.types.is_datetime64_any_dtype(hist['Timestamp']):
             hist['Timestamp'] = pd.to_datetime(hist['Timestamp'])
             
        # Filter for this volume to be safe (though usually pre-filtered)
        vol_hist = hist[hist['Volume_Name'] == investigation_result['volume']]
        if not vol_hist.empty:
            # Filter to match the graph's 24-hour window
            end_ts = vol_hist['Timestamp'].max()
            start_window = end_ts - pd.Timedelta(hours=24)
            vol_hist = vol_hist[vol_hist['Timestamp'] >= start_window]
            
            # --- Incident Duration Logic ---
            # We assume the alert was triggered by recent behavior.
            # Scan backwards to find the start of the contiguous high-latency block.
            rows = vol_hist.sort_values('Timestamp').to_dict('records')
            
            # Default to full window if logic fails
            incident_start = rows[0]['Timestamp']
            incident_end = rows[-1]['Timestamp']
            
            if rows:
                final_row = rows[-1]
                incident_end = final_row['Timestamp']
                
                # Heuristic threshold from investigation.py
                THRESHOLD = 10.0 
                
                # Search backwards for the start of the spike
                found_start = False
                temp_start = final_row['Timestamp']
                
                for row in reversed(rows):
                    if row['Latency_ms'] > THRESHOLD:
                        temp_start = row['Timestamp']
                    else:
                        # We hit normal data, so the spike started after this row
                        found_start = True
                        break
                
                # If we found a start (or if the whole log is high latency), use it
                incident_start = temp_start

            start_str = incident_start.strftime('%Y-%m-%d %H:%M:%S')
            end_str = incident_end.strftime('%Y-%m-%d %H:%M:%S')
            diff = incident_end - incident_start
            
            # Format duration nicely
            total_seconds = int(diff.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            if hours > 0:
                dur_str = f"{hours}h {minutes}m"
            else:
                dur_str = f"{minutes}m"

    pdf.set_font('Arial', 'B', 10)
    pdf.cell(30, 8, 'Investigation ID:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(60, 8, investigation_result['id'], 0, 0)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 8, 'Date:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(60, 8, investigation_result['timestamp'], 0, 1)
    
    pdf.set_x(10)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(30, 8, 'Incident Start:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(60, 8, start_str, 0, 0)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 8, 'Incident End:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(60, 8, end_str, 0, 1)

    pdf.set_x(10)
    pdf.set_x(10)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(30, 8, 'Inc. Duration:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(60, 8, dur_str, 0, 0)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 8, 'Severity:', 0, 0) # Moving severity here
    pdf.set_font('Arial', 'B', 10)
    # Color severity
    sev = investigation_result['severity']
    if sev == 'High':
        pdf.set_text_color(200, 0, 0)
    elif sev == 'Medium':
        pdf.set_text_color(200, 150, 0)
    pdf.cell(60, 8, sev, 0, 1)
    pdf.set_text_color(0, 0, 0) # Reset
    
    # 4th Row: Method | (Volume handled previously? No it was overwritten)
    pdf.set_x(10)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(30, 8, 'Method:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(60, 8, "Heuristic Behavioral Analysis", 0, 0)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 8, 'Volume:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(60, 8, investigation_result['volume'], 0, 1)
    
    # Move plain cursor below the box
    pdf.set_y(box_y + 45)
    
    # --- Executive Summary ---
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(0, 8, '  1. Executive Summary', 0, 1, 'L', fill=True)
    pdf.ln(2)
    
    findings = investigation_result['findings']
    analysis = investigation_result['analysis']
    
    pdf.set_font('Arial', '', 10)
    summary_text = (
        f"The AI Monitor detected an anomaly on volume '{investigation_result['volume']}'. "
        f"Analysis confirms a '{findings['primary_cause']}' event with {findings['confidence_score']} confidence. "
        f"Behavioral analysis indicates a '{analysis['behavior_pattern']}' pattern."
    )
    pdf.multi_cell(0, 5, summary_text)
    pdf.ln(5)
    
    # --- Technical Analysis ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, '  2. Technical Analysis (Behavioral Correlation)', 0, 1, 'L', fill=True)
    pdf.ln(2)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(40, 6, "Observed Behavior:", 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, analysis['description'])
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(40, 6, "Metrics Correlation:", 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, analysis['metrics_correlation'])
    
    # Metric Snapshot
    metrics = investigation_result['metrics']
    pdf.ln(3)
    pdf.set_font('Courier', '', 9)
    pdf.cell(10, 5, "")
    pdf.cell(50, 5, f"Latency: {metrics['Latency_ms']} ms", 1, 0)
    pdf.cell(50, 5, f"IOPS: {metrics['IOPS']}", 1, 0)
    pdf.cell(50, 5, f"Throughput: {metrics['Throughput_MB']} MB/s", 1, 1)
    pdf.ln(5)
    
    # --- Root Cause & Reasoning ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, '  3. Root Cause Hypothesis', 0, 1, 'L', fill=True)
    pdf.ln(2)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(40, 6, "Probable Cause:", 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, findings['primary_cause'], 0, 1)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(40, 6, "AI Reasoning:", 0, 0)
    pdf.set_font('Arial', '', 10)
    
    # Manual Page Break Check
    if pdf.get_y() + 30 > pdf.page_break_trigger:
        pdf.add_page()
        
    pdf.multi_cell(0, 6, findings['reasoning'])
    pdf.ln(5)
    
    # --- Recommendations ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, '  4. Recommended Actions (Advisory)', 0, 1, 'L', fill=True)
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 10)
    for i, action in enumerate(investigation_result['recommendations'], 1):
        pdf.cell(10, 6, f"{i}.", 0, 0, 'R')
        pdf.cell(0, 6, action, 0, 1)
        
    pdf.ln(20)
    
    # --- Performance Graph ---
    # Add graph if historical data is available
    if 'history' in investigation_result and not investigation_result['history'].empty:
        pdf.add_page()
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, '  5. Performance Visual Evidence', 0, 1, 'L')
        pdf.ln(5)
        
        # Generate graph image
        graph_img_path = generate_performance_chart(
            investigation_result['history'], 
            investigation_result['volume'],
            filename=f"trend_{investigation_result['id']}.png"
        )
        
        if graph_img_path:
            # Embed image
            # Width = 170 (A4 width 210 - margins 20)
            pdf.image(graph_img_path, x=15, w=180)
            pdf.ln(5)
            pdf.set_font('Arial', 'I', 9)
            pdf.cell(0, 5, 'Figure 1: Actual Latency (blue) vs Historical Baseline (gray).', 0, 1, 'C')
            
            # Cleanup temporary graph image
            try:
                os.remove(graph_img_path)
            except:
                pass
    
    # --- Disclaimer ---
    pdf.ln(20)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 4, "DISCLAIMER: This report was generated by an AI Proof-of-Concept system. The analysis is based on behavioral patterns and heuristic rules. No automated actions have been performed on the storage system. Please verify findings with standard NetApp tools.")
    
    pdf.output(filename, 'F')
    return filename

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def generate_performance_chart(history_df, volume_name, filename="chart.png"):
    """
    Generates a matplotlib chart of the performance trend and saves it as an image.
    """
    try:
        plt.figure(figsize=(10, 4))
        
        # Convert timestamps if needed
        if not pd.api.types.is_datetime64_any_dtype(history_df['Timestamp']):
             history_df['Timestamp'] = pd.to_datetime(history_df['Timestamp'])
             
        # Filter for the relevant volume
        vol_data = history_df[history_df['Volume_Name'] == volume_name].copy()
        
        # Sort by time
        vol_data = vol_data.sort_values('Timestamp')
        
        # Limit to last 24 hours for relevance (avoid 30-day squashed graph)
        if not vol_data.empty:
            last_timestamp = vol_data['Timestamp'].max()
            start_window = last_timestamp - pd.Timedelta(hours=24)
            vol_data = vol_data[vol_data['Timestamp'] >= start_window]
        
        # Plot Latency
        plt.plot(vol_data['Timestamp'], vol_data['Latency_ms'], label='Actual Latency', color='#0066cc', linewidth=1.5)
        
        # Plot Baseline as a dashed line
        if 'Upper_Bound' in vol_data.columns:
             plt.plot(vol_data['Timestamp'], vol_data['Upper_Bound'], label='Baseline (Upper Limit)', color='#999999', linestyle='--', linewidth=1)
        
        # Formatting
        plt.title(f"Latency Trend - {volume_name} (Last 24 Hours)")
        plt.ylabel("Latency (ms)")
        plt.xlabel("Time")
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.legend(loc='upper left', fontsize='small')
        
        # Date formatting on X axis - Dynamic based on range
        time_range = vol_data['Timestamp'].max() - vol_data['Timestamp'].min()
        
        if time_range.total_seconds() < 300: # Less than 5 mins
            fmt = mdates.DateFormatter('%H:%M:%S')
        elif time_range.total_seconds() < 86400: # Less than 24 hours
            fmt = mdates.DateFormatter('%H:%M')
        else:
            fmt = mdates.DateFormatter('%m-%d %H:%M')
            
        plt.gca().xaxis.set_major_formatter(fmt)
        plt.gcf().autofmt_xdate() # Rotation

        
        # Save
        plt.tight_layout()
        plt.savefig(filename, dpi=100)
        plt.close()
        
        return filename
    except Exception as e:
        print(f"[GRAPH ERROR] Could not generate graph: {e}")
        return None
