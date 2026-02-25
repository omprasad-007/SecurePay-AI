/**
 * Enterprise transaction payload contract.
 * This mirrors backend /transactions input schema.
 */
export const transactionPayloadExample = {
  upi_id: "alice@bank",
  sender_name: "Alice",
  receiver_name: "Bob",
  merchant_name: "Acme Foods",
  merchant_category: "Dining",
  transaction_amount: 1299.5,
  currency: "INR",
  transaction_type: "UPI",
  transaction_status: "SUCCESS",
  transaction_date: "2026-02-25",
  transaction_time: "18:45:00",
  geo_latitude: 12.9716,
  geo_longitude: 77.5946,
  city: "Bengaluru",
  state: "Karnataka",
  country: "India",
  ip_address: "103.21.58.10",
  device_id: "pixel-9-fp",
  device_type: "mobile",
  notes: "Customer payment",
  tags: ["priority", "upi"]
};
