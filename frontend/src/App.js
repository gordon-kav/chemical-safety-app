import React, { useState, useEffect } from 'react';
import Quagga from '@ericblade/quagga2'; // The "Stripe" Scanner
import axios from 'axios';

function App() {
  const [scanning, setScanning] = useState(false);
  const [barcode, setBarcode] = useState("Not Scanned");
  const [chemical, setChemical] = useState(null);
  const [status, setStatus] = useState("");

  // --- 1. START THE SCANNER ---
  useEffect(() => {
    if (scanning) {
      Quagga.init({
        inputStream: {
          name: "Live",
          type: "LiveStream",
          target: document.querySelector('#scanner-container'), // Target the div
          constraints: {
            facingMode: "environment", // Use Back Camera
            width: { min: 640 },
            height: { min: 480 },
            aspectRatio: { min: 1, max: 2 }
          },
        },
        locator: {
          patchSize: "medium",
          halfSample: true,
        },
        numOfWorkers: 2,
        decoder: {
          readers: [
            "code_128_reader", // Standard Chemical Labels
            "ean_reader",      // Soda cans / Books
            "ean_8_reader",
            "code_39_reader",  // Industrial
            "upc_reader"       // Retail
          ],
        },
        locate: true,
      }, (err) => {
        if (err) {
          console.error(err);
          setStatus("Error starting camera: " + err);
          return;
        }
        Quagga.start();
      });

      // What to do when a barcode is found
      Quagga.onDetected((result) => {
        if (result && result.codeResult && result.codeResult.code) {
          handleScan(result.codeResult.code);
        }
      });

      // Cleanup when we stop scanning
      return () => {
        Quagga.stop();
        Quagga.offDetected();
      };
    }
  }, [scanning]);

  // --- 2. HANDLE THE SUCCESSFUL SCAN ---
  const handleScan = (code) => {
    setScanning(false); // Stop the camera
    setBarcode(code);   // Save the number
    setStatus("Searching Cloud Database...");
    checkDatabase(code); // Ask the Cloud
  };

  // --- 3. CHECK THE CLOUD (RENDER) ---
  const checkDatabase = (code) => {
    // ⚠️ CRITICAL: Pointing to your Render Cloud Backend
    axios.get('https://chemical-safety-app.onrender.com/chemicals/')
      .then(response => {
        // Look for match
        const found = response.data.find(c => c.cas_number === code || c.name === code);
        
        if (found) {
          setChemical(found);
          setStatus("Found!");
        } else {
          setChemical(null);
          setStatus("Chemical not in database.");
        }
      })
      .catch(error => {
        console.error("Error connecting to backend:", error);
        setStatus("Error: Could not connect to Cloud Backend.");
      });
  };

  return (
    <div style={{ textAlign: "center", padding: "20px", fontFamily: "Arial" }}>
      <h1>🧪 Chemical Safety Scanner</h1>
      
      {/* CAMERA WINDOW */}
      {scanning ? (
        <div style={{ margin: "0 auto", maxWidth: "100%" }}>
          <div id="scanner-container" style={{ width: "100%", height: "300px", overflow: "hidden", border: "5px solid #333" }}>
            {/* Quagga injects the video here */}
          </div>
          <button onClick={() => setScanning(false)} style={{ marginTop: "10px", padding: "10px", fontSize: "16px" }}>
            Stop Camera
          </button>
        </div>
      ) : (
        <button 
          onClick={() => {
            setScanning(true);
            setChemical(null);
            setStatus("Starting Camera...");
          }} 
          style={{ fontSize: "18px", padding: "15px 30px", backgroundColor: "#007BFF", color: "white", border: "none", borderRadius: "5px", cursor: "pointer" }}
        >
          📷 Scan Barcode
        </button>
      )}

      {/* RESULTS */}
      <div style={{ marginTop: "30px" }}>
        <h3>Barcode: {barcode}</h3>
        <p style={{ fontWeight: "bold", color: status.includes("Error") ? "red" : "blue" }}>{status}</p>

        {chemical && (
          <div style={{ border: "1px solid #ccc", padding: "20px", borderRadius: "10px", backgroundColor: "#d4edda", maxWidth: "400px", margin: "0 auto" }}>
            <h2 style={{ color: "#155724" }}>✅ Verified: {chemical.name}</h2>
            <p><strong>Hazards:</strong> {chemical.hazards}</p>
            <p><strong>Description:</strong> {chemical.description}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;