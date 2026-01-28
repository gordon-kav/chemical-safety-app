/* eslint-disable */
import React, { useState, useEffect, useCallback } from 'react';
import Quagga from '@ericblade/quagga2';
import axios from 'axios';

function App() {
  const [scanning, setScanning] = useState(false);
  const [barcode, setBarcode] = useState("Ready to Scan");
  const [viewedChemical, setViewedChemical] = useState(null);
  const [status, setStatus] = useState("IDLE"); 
  
  // Dashboard Data
  const [totalStock, setTotalStock] = useState(null);

  // Form State
  const [formName, setFormName] = useState("");
  const [formHazards, setFormHazards] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formSDS, setFormSDS] = useState("");
  
  // --- SPLIT QUANTITY INPUTS ---
  const [formQtyValue, setFormQtyValue] = useState(""); 
  const [formQtyUnit, setFormQtyUnit] = useState("ml"); // Default to ml

  const API_URL = 'https://chemical-safety-app.onrender.com'; 

  const checkDatabase = useCallback((code) => {
    setStatus("SEARCHING");
    axios.get(`${API_URL}/chemicals/`)
      .then(response => {
        const existingType = response.data.find(c => c.cas_number === code);
        
        if (existingType) {
           // PRE-FILL FORM with existing data
           setFormName(existingType.name);
           setFormHazards(existingType.hazards);
           setFormDescription(existingType.description);
           setFormSDS(existingType.sds_link);
           setFormQtyValue(""); // Reset number for new bottle
           setFormQtyUnit(existingType.quantity_unit || "ml"); // Keep consistent unit
           
           // FETCH TOTAL STOCK for this chemical
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
      .catch(error => {
        setStatus("ERROR");
      });
  }, []);

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
    if(!formQtyValue) return alert("Please enter quantity size");

    const payload = {
      name: formName,
      cas_number: barcode, 
      hazards: formHazards || "Unknown",
      description: formDescription || "Added via App",
      sds_link: formSDS || "",
      quantity_value: parseFloat(formQtyValue), // Send as Number
      quantity_unit: formQtyUnit                // Send as Text
    };

    axios.post(`${API_URL}/chemicals/`, payload)
      .then(res => {
        alert("Bottle Added! ✅");
        setViewedChemical(res.data);
        setStatus("VIEW_BOTTLE");
      })
      .catch(err => alert("Error saving: " + err.message));
  };

  const handleScan = useCallback((code) => {
    setScanning(false);
    setBarcode(code);
    checkDatabase(code);
  }, [checkDatabase]);

  useEffect(() => {
    if (scanning) {
      Quagga.init({
        inputStream: { name: "Live", type: "LiveStream", target: document.querySelector('#scanner-container'), constraints: { facingMode: "environment" } },
        decoder: { readers: ["code_128_reader", "ean_reader", "upc_reader"] },
      }, (err) => {
        if (err) return console.error(err);
        Quagga.start();
      });
      Quagga.onDetected((result) => { if (result?.codeResult?.code) handleScan(result.codeResult.code); });
      return () => { Quagga.stop(); Quagga.offDetected(); };
    }
  }, [scanning, handleScan]);

  const styles = {
    container: { fontFamily: "sans-serif", backgroundColor: "#f4f6f9", minHeight: "100vh", paddingBottom: "50px" },
    navbar: { backgroundColor: "#2c3e50", color: "white", padding: "15px", textAlign: "center" },
    main: { maxWidth: "600px", margin: "0 auto", padding: "20px" },
    card: { backgroundColor: "white", borderRadius: "12px", padding: "20px", boxShadow: "0 4px 6px rgba(0,0,0,0.05)", marginBottom: "20px", textAlign: "center" },
    btnScan: { width: "100%", padding: "15px", fontSize: "1.1rem", fontWeight: "bold", color: "white", backgroundColor: "#3498db", border: "none", borderRadius: "8px", cursor: "pointer" },
    btnAction: { padding: "10px 20px", marginTop: "10px", backgroundColor: "#27ae60", color: "white", border: "none", borderRadius: "5px", fontWeight: "bold", cursor: "pointer", width: "100%" },
    btnAuto: { backgroundColor: "#8e44ad", marginBottom: "10px" }, 
    input: { width: "100%", padding: "10px", margin: "5px 0 15px 0", borderRadius: "5px", border: "1px solid #ddd", boxSizing: "border-box" },
    row: { display: "flex", gap: "10px" },
    select: { padding: "10px", borderRadius: "5px", border: "1px solid #ddd", backgroundColor: "white" }
  };

  return (
    <div style={styles.container}>
      <nav style={styles.navbar}><h3>🧪 Lab Safety & Inventory</h3></nav>
      <main style={styles.main}>
        
        {scanning ? (
           <div style={styles.card}>
             <div id="scanner-container" style={{ height: "250px", overflow: "hidden" }}></div>
             <button onClick={() => setScanning(false)} style={{...styles.btnScan, backgroundColor: "#e74c3c", marginTop: "10px"}}>Stop</button>
           </div>
        ) : (
           <button onClick={() => { setScanning(true); setStatus("SCANNING"); }} style={styles.btnScan}>📷 Scan Barcode</button>
        )}

        {/* VIEW NEW BOTTLE */}
        {status === "VIEW_BOTTLE" && viewedChemical && (
          <div style={{ ...styles.card, textAlign: "center" }}>
            <h2 style={{color: "green"}}>✅ Bottle Added!</h2>
            <h3>{viewedChemical.name}</h3>
            <p><strong>Size:</strong> {viewedChemical.quantity_value} {viewedChemical.quantity_unit}</p>
            <div style={{marginTop: "20px", borderTop: "2px dashed #eee", paddingTop: "20px"}}>
                <img src={`https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${viewedChemical.tracking_id}`} alt="QR" />
                <p style={{fontSize: "0.8rem", color: "#888"}}>Tracking ID: {viewedChemical.tracking_id}</p>
            </div>
            <button onClick={() => setStatus("IDLE")} style={{...styles.btnAction, backgroundColor: "#95a5a6"}}>Done</button>
          </div>
        )}

        {/* ADD FORM */}
        {(status === "NOT_FOUND" || status === "FOUND_TYPE") && (
           <div style={{ ...styles.card, textAlign: "left" }}>
             <h3>➕ Add Bottle</h3>
             
             {/* TOTAL STOCK DASHBOARD */}
             {totalStock && (
                 <div style={{backgroundColor: "#d1ecf1", padding: "10px", borderRadius: "5px", marginBottom: "15px", border: "1px solid #bee5eb"}}>
                     <h4 style={{margin: "0 0 5px 0", color: "#0c5460"}}>📊 Current Stock:</h4>
                     <p style={{margin: 0}}>
                         <strong>{totalStock.total_stock} {totalStock.unit}</strong> 
                         <span> (across {totalStock.bottle_count} bottles)</span>
                     </p>
                 </div>
             )}

             <label>Product Name:</label>
             <input style={styles.input} placeholder="e.g. Acetone" value={formName} onChange={e => setFormName(e.target.value)} />
             
             {status === "NOT_FOUND" && (
                <button onClick={handleAutoFill} style={{...styles.btnAction, ...styles.btnAuto}}>✨ Auto-Fill</button>
             )}

             <label>Hazards:</label>
             <input style={styles.input} value={formHazards} onChange={e => setFormHazards(e.target.value)} />

             <label>SDS Link:</label>
             <input style={styles.input} value={formSDS} onChange={e => setFormSDS(e.target.value)} />

             {/* SPLIT QUANTITY INPUTS */}
             <label>Container Size:</label>
             <div style={styles.row}>
                 <input 
                    type="number" 
                    style={{...styles.input, flex: 2}} 
                    placeholder="e.g. 500" 
                    value={formQtyValue}
                    onChange={e => setFormQtyValue(e.target.value)} 
                 />
                 <select 
                    style={{...styles.select, flex: 1, height: "42px", marginTop: "5px"}} 
                    value={formQtyUnit}
                    onChange={e => setFormQtyUnit(e.target.value)}
                 >
                     <option value="ml">ml</option>
                     <option value="L">L</option>
                     <option value="g">g</option>
                     <option value="kg">kg</option>
                     <option value="gal">gal</option>
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