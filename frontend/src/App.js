/* eslint-disable */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Html5QrcodeScanner } from "html5-qrcode";
import axios from 'axios';

function App() {
  // Modes: "SCAN_MODE" (Default) or "USAGE_MODE" (Deducting)
  const [appMode, setAppMode] = useState("INVENTORY"); 
  
  const [scanning, setScanning] = useState(false);
  const [barcode, setBarcode] = useState("Ready to Scan");
  const [viewedChemical, setViewedChemical] = useState(null);
  const [status, setStatus] = useState("IDLE"); 
  const [totalStock, setTotalStock] = useState(null);

  // Form State
  const [formName, setFormName] = useState("");
  const [formHazards, setFormHazards] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formSDS, setFormSDS] = useState("");
  const [formQtyValue, setFormQtyValue] = useState(""); 
  const [formQtyUnit, setFormQtyUnit] = useState("ml"); 
  
  // Usage State
  const [usageAmount, setUsageAmount] = useState("");

  const API_URL = 'https://chemical-safety-app.onrender.com'; 
  const scannerRef = useRef(null);

  // --- 1. SCANNING LOGIC ---
  const handleScanSuccess = useCallback((decodedText) => {
    if (scannerRef.current) {
        scannerRef.current.clear().catch(err => console.error(err));
        setScanning(false);
    }
    setBarcode(decodedText);
    console.log("Scanned:", decodedText);

    // LOGIC: Is this a Tracking ID (8 chars) or a Barcode?
    const isTrackingID = decodedText.length === 8 && !decodedText.match(/^\d+$/); 

    if (appMode === "CHECKOUT" || isTrackingID) {
        handleUsageScan(decodedText);
    } else {
        checkDatabase(decodedText);
    }
  }, [appMode]);

  // --- 2. INVENTORY LOOKUP ---
  const checkDatabase = (code) => {
    setStatus("SEARCHING");
    axios.get(`${API_URL}/chemicals/`)
      .then(response => {
        const existingType = response.data.find(c => c.cas_number === code);
        if (existingType) {
           setFormName(existingType.name);
           setFormHazards(existingType.hazards);
           setFormDescription(existingType.description);
           setFormSDS(existingType.sds_link);
           setFormQtyValue(""); 
           setFormQtyUnit(existingType.quantity_unit || "ml");
           
           axios.get(`${API_URL}/total_stock/${existingType.name}`)
                .then(res => setTotalStock(res.data))
                .catch(e => console.log(e));

           setStatus("FOUND_TYPE"); 
        } else {
          setFormName("");
          setFormHazards("");
          setFormDescription("");
          setFormSDS("");
          setFormQtyValue("");
          setTotalStock(null);
          setStatus("NOT_FOUND");
        }
      })
      .catch(error => setStatus("ERROR"));
  };

  // --- 3. USAGE / DEDUCT LOGIC ---
  const handleUsageScan = (trackingId) => {
      axios.get(`${API_URL}/chemicals/`)
        .then(res => {
            const bottle = res.data.find(c => c.tracking_id === trackingId);
            if(bottle) {
                setViewedChemical(bottle);
                setStatus("USAGE_FOUND");
            } else {
                alert("Tracking ID not found in system.");
            }
        });
  };

  const handleDeduct = () => {
      if(!usageAmount) return alert("Enter amount used");
      
      axios.post(`${API_URL}/use_chemical/`, {
          tracking_id: viewedChemical.tracking_id,
          amount_used: parseFloat(usageAmount)
      }).then(res => {
          alert(`Success! Remaining: ${res.data.remaining_quantity} ${res.data.unit}`);
          setStatus("IDLE");
          setUsageAmount("");
          setViewedChemical(null);
      }).catch(err => alert("Error updating stock"));
  };

  // --- 4. ADD NEW ITEM LOGIC ---
  const handleAutoFill = () => {
    if(!formName) return alert("Type name first");
    axios.get(`${API_URL}/autofill/${formName}`).then(res => {
        if(res.data.found) {
           setFormHazards(res.data.hazards);
           setFormDescription(res.data.description);
           setFormSDS(res.data.sds_link || "");
        } else alert("Not found");
    });
  };

  const handleSave = () => {
    if(!formQtyValue) return alert("Enter quantity");
    const payload = {
      name: formName,
      cas_number: barcode, 
      hazards: formHazards || "Unknown",
      description: formDescription || "Added via App",
      sds_link: formSDS || "",
      quantity_value: parseFloat(formQtyValue), 
      quantity_unit: formQtyUnit
    };
    axios.post(`${API_URL}/chemicals/`, payload)
      .then(res => {
        alert("Saved! ✅");
        setViewedChemical(res.data);
        setStatus("VIEW_BOTTLE");
      })
      .catch(err => alert("Error saving: " + err.message));
  };

  const handleDownload = () => window.location.href = `${API_URL}/export_csv`;

  // --- 5. SCANNER EFFECT ---
  useEffect(() => {
      if(scanning) {
          const scanner = new Html5QrcodeScanner("reader", { fps: 10, qrbox: 250 });
          scanner.render(handleScanSuccess, (err) => console.log(err));
          scannerRef.current = scanner;
      }
      return () => {
          if(scannerRef.current) scannerRef.current.clear().catch(e => console.error(e));
      }
  }, [scanning, handleScanSuccess]);

  const styles = {
    container: { fontFamily: "sans-serif", backgroundColor: "#f4f6f9", minHeight: "100vh", paddingBottom: "50px" },
    navbar: { backgroundColor: appMode === "INVENTORY" ? "#2c3e50" : "#c0392b", color: "white", padding: "15px", display: "flex", justifyContent: "space-between", alignItems: "center" },
    main: { maxWidth: "600px", margin: "0 auto", padding: "20px" },
    card: { backgroundColor: "white", borderRadius: "12px", padding: "20px", boxShadow: "0 4px 6px rgba(0,0,0,0.05)", marginBottom: "20px", textAlign: "center" },
    btnScan: { width: "100%", padding: "15px", fontSize: "1.1rem", fontWeight: "bold", color: "white", backgroundColor: "#3498db", border: "none", borderRadius: "8px", cursor: "pointer" },
    btnDeduct: { width: "100%", padding: "15px", fontSize: "1.1rem", fontWeight: "bold", color: "white", backgroundColor: "#e74c3c", border: "none", borderRadius: "8px", cursor: "pointer" },
    btnAction: { padding: "10px 20px", marginTop: "10px", backgroundColor: "#27ae60", color: "white", border: "none", borderRadius: "5px", fontWeight: "bold", cursor: "pointer", width: "100%" },
    btnExport: { backgroundColor: "#f1c40f", color: "#2c3e50", border: "none", padding: "8px 15px", borderRadius: "4px", fontWeight: "bold", cursor: "pointer" },
    input: { width: "100%", padding: "10px", margin: "5px 0 15px 0", borderRadius: "5px", border: "1px solid #ddd", boxSizing: "border-box" },
    row: { display: "flex", gap: "10px" },
    select: { padding: "10px", borderRadius: "5px", border: "1px solid #ddd", backgroundColor: "white" }
  };

  return (
    <div style={styles.container}>
      <nav style={styles.navbar}>
          <div onClick={() => setAppMode(appMode === "INVENTORY" ? "CHECKOUT" : "INVENTORY")} style={{cursor: "pointer", fontWeight: "bold"}}>
              {appMode === "INVENTORY" ? "📦 INVENTORY" : "📤 CHECKOUT"} 
              <span style={{fontSize: "0.7rem", fontWeight: "normal", opacity: 0.8}}>(Tap to Switch)</span>
          </div>
          <button onClick={handleDownload} style={styles.btnExport}>⬇ CSV</button>
      </nav>

      <main style={styles.main}>
        {scanning ? (
           <div style={styles.card}>
             <div id="reader" width="100%"></div>
             <button onClick={() => { setScanning(false); if(scannerRef.current) scannerRef.current.clear(); }} style={{...styles.btnScan, backgroundColor: "#7f8c8d", marginTop: "10px"}}>Close Scanner</button>
           </div>
        ) : (
           <button 
                onClick={() => { setScanning(true); setStatus("SCANNING"); }} 
                style={appMode === "INVENTORY" ? styles.btnScan : styles.btnDeduct}
            >
               {appMode === "INVENTORY" ? "📷 Scan to ADD Stock" : "📷 Scan QR to USE Stock"}
           </button>
        )}

        {/* --- USAGE / DEDUCT SCREEN --- */}
        {status === "USAGE_FOUND" && viewedChemical && (
             <div style={{...styles.card, border: "2px solid #e74c3c"}}>
                <h3 style={{color: "#c0392b"}}>Deduct from Stock</h3>
                <h2>{viewedChemical.name}</h2>
                <p>Current Level: <strong>{viewedChemical.quantity_value} {viewedChemical.quantity_unit}</strong></p>
                <label style={{display:"block", textAlign:"left", fontWeight:"bold"}}>Amount Used:</label>
                <div style={styles.row}>
                    <input type="number" style={styles.input} placeholder="e.g. 50" value={usageAmount} onChange={e => setUsageAmount(e.target.value)} />
                    <span style={{paddingTop: "15px", fontWeight: "bold"}}>{viewedChemical.quantity_unit}</span>
                </div>
                <button onClick={handleDeduct} style={{...styles.btnAction, backgroundColor: "#c0392b"}}>Confirm Usage 📉</button>
                <button onClick={() => setStatus("IDLE")} style={{...styles.btnAction, backgroundColor: "#95a5a6", marginTop: "5px"}}>Cancel</button>
             </div>
        )}

        {/* --- INVENTORY VIEWING SCREEN --- */}
        {status === "VIEW_BOTTLE" && viewedChemical && (
          <div style={{ ...styles.card, textAlign: "center" }}>
            <h2 style={{color: "green"}}>✅ Bottle Added!</h2>
            <h3>{viewedChemical.name}</h3>
            <img src={`https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${viewedChemical.tracking_id}`} alt="QR" style={{marginTop: "10px"}} />
            <p style={{fontSize:"0.8rem"}}>ID: {viewedChemical.tracking_id}</p>
            <button onClick={() => setStatus("IDLE")} style={{...styles.btnAction, backgroundColor: "#95a5a6"}}>Done</button>
          </div>
        )}

        {/* --- ADD NEW BOTTLE FORM --- */}
        {(status === "NOT_FOUND" || status === "FOUND_TYPE") && appMode === "INVENTORY" && (
           <div style={{ ...styles.card, textAlign: "left" }}>
             <h3>➕ Add Bottle</h3>
             {totalStock && (
                 <div style={{backgroundColor: "#d1ecf1", padding: "10px", borderRadius: "5px", marginBottom: "15px"}}>
                     📊 Total Stock: <strong>{totalStock.total_stock} {totalStock.unit}</strong> 
                 </div>
             )}
             <label>Product Name:</label>
             <input style={styles.input} value={formName} onChange={e => setFormName(e.target.value)} />
             
             {status === "NOT_FOUND" && <button onClick={handleAutoFill} style={{...styles.btnAction, backgroundColor: "#8e44ad", marginBottom: "10px"}}>✨ Auto-Fill</button>}

             <label>Hazards:</label>
             <input style={styles.input} value={formHazards} onChange={e => setFormHazards(e.target.value)} />
             <label>SDS Link:</label>
             <input style={styles.input} value={formSDS} onChange={e => setFormSDS(e.target.value)} />
             <label>Container Size:</label>
             <div style={styles.row}>
                 <input type="number" style={{...styles.input, flex: 2}} value={formQtyValue} onChange={e => setFormQtyValue(e.target.value)} />
                 <select style={{...styles.select, flex: 1, height: "42px", marginTop: "5px"}} value={formQtyUnit} onChange={e => setFormQtyUnit(e.target.value)}>
                     <option value="ml">ml</option><option value="L">L</option><option value="g">g</option><option value="kg">kg</option>
                 </select>
             </div>
             <button onClick={handleSave} style={styles.btnAction}>💾 Save & Print QR</button>
           </div>
        )}
      </main>
    </div>
  );
}

export default App;