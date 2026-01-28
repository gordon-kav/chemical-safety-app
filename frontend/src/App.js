/* eslint-disable */
import React, { useState, useEffect, useCallback } from 'react';
import Quagga from '@ericblade/quagga2';
import axios from 'axios';

function App() {
  const [scanning, setScanning] = useState(false);
  const [barcode, setBarcode] = useState("Ready to Scan");
  const [chemical, setChemical] = useState(null);
  const [status, setStatus] = useState("IDLE"); 
  
  // --- NEW: Form State ---
  const [formName, setFormName] = useState("");
  const [formHazards, setFormHazards] = useState("");
  const [formDescription, setFormDescription] = useState("");

  const API_URL = 'https://chemical-safety-app.onrender.com'; // Your Backend URL

  const checkDatabase = useCallback((code) => {
    setStatus("SEARCHING");
    axios.get(`${API_URL}/chemicals/`)
      .then(response => {
        const found = response.data.find(c => c.cas_number === code);
        if (found) {
          setChemical(found);
          setStatus("FOUND");
        } else {
          setChemical(null);
          setStatus("NOT_FOUND");
          // Reset form for new entry
          setFormName("");
          setFormHazards("");
          setFormDescription("");
        }
      })
      .catch(error => {
        console.error("Backend Error:", error);
        setStatus("ERROR");
      });
  }, []);

  // --- NEW: Auto-Fill Function ---
  const handleAutoFill = () => {
    if(!formName) return alert("Please type a name first (e.g. 'Bleach')");
    
    // Call your new intelligent endpoint
    axios.get(`${API_URL}/autofill/${formName}`)
      .then(res => {
        if(res.data.found) {
           setFormHazards(res.data.hazards);
           setFormDescription(res.data.description);
           alert("Data found via PubChem! 🧪");
        } else {
           alert("Could not find data in PubChem. You can type it manually.");
        }
      })
      .catch(err => alert("Error connecting to intelligence engine."));
  };

  // --- NEW: Save Function ---
  const handleSave = () => {
    const payload = {
      name: formName,
      cas_number: barcode, // We use the barcode as the ID
      hazards: formHazards || "Unknown",
      description: formDescription || "Added via App"
    };

    axios.post(`${API_URL}/chemicals/`, payload)
      .then(res => {
        alert("Saved to Inventory! ✅");
        setStatus("FOUND");
        setChemical(res.data); // Show the newly saved card
      })
      .catch(err => {
        console.error(err);
        alert("Error saving: " + err.message);
      });
  };

  const handleScan = useCallback((code) => {
    setScanning(false);
    setBarcode(code);
    checkDatabase(code);
  }, [checkDatabase]);

  useEffect(() => {
    if (scanning) {
      Quagga.init({
        inputStream: {
          name: "Live",
          type: "LiveStream",
          target: document.querySelector('#scanner-container'),
          constraints: { facingMode: "environment" },
        },
        decoder: { readers: ["code_128_reader", "ean_reader", "upc_reader"] },
      }, (err) => {
        if (err) return console.error(err);
        Quagga.start();
      });

      Quagga.onDetected((result) => {
        if (result?.codeResult?.code) handleScan(result.codeResult.code);
      });

      return () => { Quagga.stop(); Quagga.offDetected(); };
    }
  }, [scanning, handleScan]);

  // --- STYLES ---
  const styles = {
    container: { fontFamily: "sans-serif", backgroundColor: "#f4f6f9", minHeight: "100vh", paddingBottom: "50px" },
    navbar: { backgroundColor: "#2c3e50", color: "white", padding: "15px", textAlign: "center" },
    main: { maxWidth: "600px", margin: "0 auto", padding: "20px" },
    card: { backgroundColor: "white", borderRadius: "12px", padding: "20px", boxShadow: "0 4px 6px rgba(0,0,0,0.05)", marginBottom: "20px", textAlign: "center" },
    btnScan: { width: "100%", padding: "15px", fontSize: "1.1rem", fontWeight: "bold", color: "white", backgroundColor: "#3498db", border: "none", borderRadius: "8px", cursor: "pointer" },
    btnAction: { padding: "10px 20px", marginTop: "10px", backgroundColor: "#27ae60", color: "white", border: "none", borderRadius: "5px", fontWeight: "bold", cursor: "pointer", width: "100%" },
    btnAuto: { backgroundColor: "#8e44ad", marginBottom: "10px" }, // Purple button
    input: { width: "100%", padding: "10px", margin: "5px 0 15px 0", borderRadius: "5px", border: "1px solid #ddd", boxSizing: "border-box" },
    label: { display: "block", textAlign: "left", fontWeight: "bold", color: "#555" }
  };

  const getStatusColor = () => {
    if (status === "FOUND") return "#d4edda";
    if (status === "NOT_FOUND") return "#f8d7da";
    return "#e2e3e5";
  };

  return (
    <div style={styles.container}>
      <nav style={styles.navbar}><h1>🧪 Chemical Safety</h1></nav>
      <main style={styles.main}>
        
        {scanning ? (
          <div style={styles.card}>
            <div id="scanner-container" style={{ height: "250px", overflow: "hidden" }}></div>
            <button onClick={() => setScanning(false)} style={{...styles.btnScan, backgroundColor: "#e74c3c", marginTop: "10px"}}>Stop</button>
          </div>
        ) : (
          <button onClick={() => { setScanning(true); setStatus("SCANNING"); }} style={styles.btnScan}>📷 Scan Barcode</button>
        )}

        <div style={{...styles.card, backgroundColor: getStatusColor() }}>
           <p>Barcode: <strong>{barcode}</strong></p>
           <h3>{status === "FOUND" ? "✅ Verified Safe" : status === "NOT_FOUND" ? "⚠️ Not in Database" : "Ready"}</h3>
        </div>

        {/* 1. VIEW EXISTING CHEMICAL */}
        {chemical && (
          <div style={{ ...styles.card, textAlign: "left" }}>
            <h2>{chemical.name}</h2>
            <p>{chemical.description}</p>
            <div style={{backgroundColor: "#fff3cd", padding: "10px", borderRadius: "5px"}}>
              <strong>⚠️ Hazards:</strong> {chemical.hazards}
            </div>
          </div>
        )}

        {/* 2. ADD NEW CHEMICAL FORM */}
        {status === "NOT_FOUND" && (
           <div style={{ ...styles.card, textAlign: "left" }}>
             <h3>➕ Add New Item</h3>
             
             <label style={styles.label}>Product Name:</label>
             <input 
                style={styles.input} 
                placeholder="e.g. Clorox Bleach" 
                value={formName}
                onChange={e => setFormName(e.target.value)}
             />

             {/* The Intelligent Button */}
             <button onClick={handleAutoFill} style={{...styles.btnAction, ...styles.btnAuto}}>
                ✨ Auto-Fill Hazards (PubChem)
             </button>

             <label style={styles.label}>Hazards:</label>
             <input 
                style={styles.input} 
                value={formHazards}
                onChange={e => setFormHazards(e.target.value)}
             />

             <label style={styles.label}>Description:</label>
             <input 
                style={styles.input} 
                value={formDescription}
                onChange={e => setFormDescription(e.target.value)}
             />

             <button onClick={handleSave} style={styles.btnAction}>💾 Save to Database</button>
           </div>
        )}

      </main>
    </div>
  );
}

export default App;