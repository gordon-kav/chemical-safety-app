 import React, { useState } from 'react';
import BarcodeScannerComponent from "react-qr-barcode-scanner";
import axios from 'axios';

function App() {
  const [scanning, setScanning] = useState(false);
  const [barcode, setBarcode] = useState("Not Scanned");
  const [chemical, setChemical] = useState(null);
  const [status, setStatus] = useState("");

  // 1. This function runs when the camera sees a barcode
  const handleScan = async (err, result) => {
    if (result) {
      setScanning(false); // Stop the camera
      setBarcode(result.text); // Save the barcode number
      setStatus("Searching database...");
      checkDatabase(result.text); // Ask Python about it
    }
  };

  // 2. This function talks to your Python Backend
  const checkDatabase = (code) => {
    // We will fetch all chemicals and look for a match
    axios.get('/http://10.208.170.10:8000/chemicals/')
      .then(response => {
        // Look for the barcode in the 'cas_number' or 'id' field
        const found = response.data.find(c => c.cas_number === code || c.name === code);
        
        if (found) {
          setChemical(found);
          setStatus("Found!");
        } else {
          setChemical(null);
          setStatus("Chemical not in database. Would you like to add it?");
        }
      })
      .catch(error => {
        console.error("Error connecting to backend:", error);
        setStatus("Error: Could not connect to Python backend.");
      });
  };

  return (
    <div style={{ textAlign: "center", padding: "20px", fontFamily: "Arial" }}>
      <h1>🧪 Chemical Safety Scanner</h1>
      
      {/* The Camera Window */}
      {scanning ? (
        <div style={{ margin: "0 auto", width: "300px", border: "5px solid #333" }}>
          <BarcodeScannerComponent
            width={300}
            height={300}
            onUpdate={handleScan}
          />
          <button onClick={() => setScanning(false)} style={{ marginTop: "10px", padding: "10px" }}>
            Stop Camera
          </button>
        </div>
      ) : (
        <button 
          onClick={() => {
            setScanning(true);
            setChemical(null);
            setStatus("");
          }} 
          style={{ fontSize: "18px", padding: "15px 30px", backgroundColor: "#007BFF", color: "white", border: "none", borderRadius: "5px", cursor: "pointer" }}
        >
          📷 Scan Barcode
        </button>
      )}

      {/* Results Section */}
      <div style={{ marginTop: "30px" }}>
        <h3>Barcode: {barcode}</h3>
        <p style={{ fontWeight: "bold", color: "red" }}>{status}</p>

        {chemical && (
          <div style={{ border: "1px solid #ccc", padding: "20px", borderRadius: "10px", backgroundColor: "#f9f9f9", maxWidth: "400px", margin: "0 auto" }}>
            <h2 style={{ color: "green" }}>✅ Verified: {chemical.name}</h2>
            <p><strong>Hazards:</strong> {chemical.hazards}</p>
            <p><strong>Description:</strong> {chemical.description}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;

