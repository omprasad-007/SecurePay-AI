import React from "react";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

export default function TransactionMap({ transactions = [] }) {
  const points = transactions.filter((tx) => tx.geo_latitude != null && tx.geo_longitude != null);

  if (!points.length) {
    return <div className="card p-4 text-sm text-muted">No geolocation points available.</div>;
  }

  const center = [points[0].geo_latitude, points[0].geo_longitude];

  return (
    <div className="card p-4">
      <h3 className="font-semibold mb-3">Transaction Map View</h3>
      <div className="h-72 rounded-xl overflow-hidden">
        <MapContainer center={center} zoom={5} className="h-full w-full">
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {points.map((tx) => (
            <Marker key={tx.transaction_id} position={[tx.geo_latitude, tx.geo_longitude]}>
              <Popup>
                <div className="text-sm">
                  <p><strong>{tx.merchant_name}</strong></p>
                  <p>{tx.currency} {tx.transaction_amount}</p>
                  <p>Risk: {tx.risk_score}</p>
                  <p>{tx.city}, {tx.country}</p>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
