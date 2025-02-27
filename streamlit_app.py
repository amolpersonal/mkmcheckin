##import streamlit as st
##
##st.title("🎈 My new app")
##st.write(
##    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
##)

import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import json
from streamlit_javascript import st_javascript

# Page configuration
st.set_page_config(
    page_title="Event Check-in System",
    page_icon="🎟️",
    layout="wide"
)

# Initialize session state
if 'scan_mode' not in st.session_state:
    st.session_state.scan_mode = True
if 'last_scanned_code' not in st.session_state:
    st.session_state.last_scanned_code = None
if 'checked_in_attendees' not in st.session_state:
    st.session_state.checked_in_attendees = 0
if 'type_a_count' not in st.session_state:
    st.session_state.type_a_count = 0
if 'type_b_count' not in st.session_state:
    st.session_state.type_b_count = 0
if 'qr_scanner_result' not in st.session_state:
    st.session_state.qr_scanner_result = None

# Function to authenticate with Google Sheets
@st.cache_resource
def authenticate_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    # You'll need to upload your JSON credentials file to Streamlit Secrets Management
    # or deploy with environment variables
    try:
        # Try to load from secrets first (for Streamlit Cloud deployment)
        credentials_dict = st.secrets["google_credentials"]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    except Exception as e:
        st.error(f"Failed to load credentials from secrets: {e}")
        # For local testing with a credentials file
        try:
            credentials = ServiceAccountCredentials.from_json_keyfile_name("mkmcheckin-1e1b8f4a7ea2.json", scope)
        except Exception as e:
            st.error(f"Failed to load credentials from file: {e}")
            return None

    client = gspread.authorize(credentials)
    return client

# Function to load attendee data
def load_attendee_data(sheet_url):
    client = authenticate_google_sheets()
    if client is None:
        return pd.DataFrame()

    try:
        # Open the spreadsheet by URL
        sheet = client.open_by_url(sheet_url)

        # Get the first worksheet
        worksheet = sheet.get_worksheet(0)

        # Get all data from the worksheet
        data = worksheet.get_all_records()

        # Convert to DataFrame
        df = pd.DataFrame(data)

        return df
    except Exception as e:
        st.error(f"Error loading spreadsheet data: {e}")
        return pd.DataFrame()


# JavaScript for QR code scanning
def inject_qr_scanner():
    js_code = """
    async function setupScanner() {
        // Make sure jsQR is loaded
        if (!window.jsQR) {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js';
            document.head.appendChild(script);
            await new Promise(resolve => script.onload = resolve);
        }

        // Setup video element and canvas if they don't exist
        if (!window.qrVideo) {
            // Create container for video and canvas
            const container = document.createElement('div');
            container.style.position = 'relative';
            container.style.width = '100%';
            container.style.maxWidth = '500px';
            container.style.margin = '0 auto';

            // Create video element
            window.qrVideo = document.createElement('video');
            window.qrVideo.id = 'qr-video';
            window.qrVideo.style.width = '100%';
            window.qrVideo.style.borderRadius = '10px';
            container.appendChild(window.qrVideo);

            // Create canvas for scan visualization
            window.qrCanvas = document.createElement('canvas');
            window.qrCanvas.id = 'qr-canvas';
            window.qrCanvas.style.position = 'absolute';
            window.qrCanvas.style.top = '0';
            window.qrCanvas.style.left = '0';
            window.qrCanvas.style.width = '100%';
            window.qrCanvas.style.height = '100%';
            window.qrCanvas.style.objectFit = 'contain';
            container.appendChild(window.qrCanvas);

            // Insert container where the "QR Scanner" placeholder is
            const scannerPlaceholder = document.getElementById('qr-scanner-placeholder');
            if (scannerPlaceholder) {
                scannerPlaceholder.appendChild(container);
            } else {
                // Fallback to appending to body
                document.body.appendChild(container);
            }
        }

        // Start video stream if not already started
        if (!window.videoStream) {
            try {
                window.videoStream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: "environment" }
                });
                window.qrVideo.srcObject = window.videoStream;
                window.qrVideo.setAttribute('playsinline', true);
                window.qrVideo.play();

                // Start scanning
                window.scanInterval = setInterval(scanQRCode, 100);
            } catch (error) {
                console.error("Error accessing camera:", error);
                return { error: "Failed to access camera: " + error.message };
            }
        }

        return { status: "Scanner started" };
    }

    function scanQRCode() {
        if (!window.jsQR || !window.qrVideo || !window.qrCanvas) return;

        if (window.qrVideo.readyState === window.qrVideo.HAVE_ENOUGH_DATA) {
            // Set canvas dimensions to match video
            window.qrCanvas.width = window.qrVideo.videoWidth;
            window.qrCanvas.height = window.qrVideo.videoHeight;

            // Draw video frame to canvas
            const ctx = window.qrCanvas.getContext('2d');
            ctx.drawImage(window.qrVideo, 0, 0, window.qrCanvas.width, window.qrCanvas.height);

            // Get image data for QR detection
            const imageData = ctx.getImageData(0, 0, window.qrCanvas.width, window.qrCanvas.height);

            // Scan for QR code
            const code = jsQR(imageData.data, imageData.width, imageData.height, {
                inversionAttempts: "dontInvert",
            });

            if (code) {
                // Draw indicator around QR code
                ctx.beginPath();
                ctx.lineWidth = 4;
                ctx.strokeStyle = "#FF3B58";
                ctx.moveTo(code.location.topLeftCorner.x, code.location.topLeftCorner.y);
                ctx.lineTo(code.location.topRightCorner.x, code.location.topRightCorner.y);
                ctx.lineTo(code.location.bottomRightCorner.x, code.location.bottomRightCorner.y);
                ctx.lineTo(code.location.bottomLeftCorner.x, code.location.bottomLeftCorner.y);
                ctx.lineTo(code.location.topLeftCorner.x, code.location.topLeftCorner.y);
                ctx.stroke();

                // Stop interval and video stream
                clearInterval(window.scanInterval);
                if (window.videoStream) {
                    window.videoStream.getTracks().forEach(track => track.stop());
                    window.videoStream = null;
                }

                // Return the QR code data
                window.scannedCode = code.data;
                return code.data;
            }
        }
        return null;
    }

    function stopScanner() {
        if (window.scanInterval) {
            clearInterval(window.scanInterval);
        }
        if (window.videoStream) {
            window.videoStream.getTracks().forEach(track => track.stop());
            window.videoStream = null;
        }
        return { status: "Scanner stopped" };
    }

    function getScannedCode() {
        const result = window.scannedCode;
        window.scannedCode = null;  // Reset after reading
        return result;
    }

    // Initialize and return setup result
    return await setupScanner();
    """
    return st_javascript(js_code)


def check_for_qr_code():
    js_code = """
    function getScannedCode() {
        const result = window.scannedCode;
        if (result) {
            window.scannedCode = null;  // Reset after reading
        }
        return result;
    }
    return getScannedCode();
    """
    return st_javascript(js_code)

def stop_qr_scanner():
    js_code = """
    function stopScanner() {
        if (window.scanInterval) {
            clearInterval(window.scanInterval);
        }
        if (window.videoStream) {
            window.videoStream.getTracks().forEach(track => track.stop());
            window.videoStream = null;
        }
        return { status: "Scanner stopped" };
    }
    return stopScanner();
    """
    return st_javascript(js_code)


# Function to update attendance in Google Sheets
def update_attendance(sheet_url, attendee_id, checked_in=True):
    client = authenticate_google_sheets()
    if client is None:
        return False

    try:
        # Open the spreadsheet
        sheet = client.open_by_url(sheet_url)
        worksheet = sheet.get_worksheet(0)

        # Find the row with the matching attendee ID
        all_data = worksheet.get_all_records()

        for i, row in enumerate(all_data):
            if str(row.get('ID', '')) == str(attendee_id):
                # Update the "Checked In" column (adjust column name as needed)
                worksheet.update_cell(i + 2, 5, "Yes" if checked_in else "No")  # Assuming column E is for "Checked In"

                # Also update the timestamp
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                worksheet.update_cell(i + 2, 6, timestamp)  # Assuming column F is for timestamp

                return True

        st.warning(f"Attendee ID {attendee_id} not found in spreadsheet!")
        return False
    except Exception as e:
        st.error(f"Error updating spreadsheet: {e}")
        return False


# Main app functionality
def main():
    st.title("🎟️ Event Check-in System")

    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        sheet_url = st.text_input("Google Sheet URL", value="https://docs.google.com/spreadsheets/d/1ulTHIifvgsuu-Hys21H6T5gkWiwD57huR7uEZUh90HY/edit")

        if st.button("Load Attendees"):
            df = load_attendee_data(sheet_url)
            if not df.empty:
                st.session_state.attendees_df = df
                st.success(f"Loaded {len(df)} attendees!")

                # Calculate counts by ticket type
                if 'Ticket Type' in df.columns and 'Checked In' in df.columns:
                    checked_in = df[df['Checked In'] == 'Yes']
                    st.session_state.checked_in_attendees = len(checked_in)

                    # Count by ticket type
                    for ticket_type in df['Ticket Type'].unique():
                        count = len(checked_in[checked_in['Ticket Type'] == ticket_type])
                        if ticket_type.lower() == 'type a':
                            st.session_state.type_a_count = count
                        elif ticket_type.lower() == 'type b':
                            st.session_state.type_b_count = count
            else:
                st.error("Failed to load attendee data.")

        if st.button("Reset Scanner"):
            st.session_state.scan_mode = True
            st.session_state.last_scanned_code = None
            st.rerun()

        # Display stats
        st.header("Check-in Stats")
        st.metric("Total Checked In", st.session_state.checked_in_attendees)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Type A Tickets", st.session_state.type_a_count)
        with col2:
            st.metric("Type B Tickets", st.session_state.type_b_count)

    # Main content
    if st.session_state.scan_mode:
        st.header("Scan QR Code")
        st.info("Align the QR code with the camera to scan.")

        
        # Placeholder for QR scanner
        scanner_placeholder = st.empty()
        with scanner_placeholder:
            st.markdown('<div id="qr-scanner-placeholder"></div>', unsafe_allow_html=True)
        
        # Setup QR scanner
        scanner_result = inject_qr_scanner()
        
        # Check for scanned QR code
        qr_code = check_for_qr_code()
        
        if qr_code:
            st.session_state.last_scanned_code = qr_code
            st.session_state.scan_mode = False
            stop_qr_scanner()
            st.rerun()
            
        # Manual code entry option
        st.markdown("---")
        st.subheader("Manual Entry")
        manual_code = st.text_input("Enter Attendee ID")
        if st.button("Process Manual Entry") and manual_code:
            st.session_state.last_scanned_code = manual_code
            st.session_state.scan_mode = False
            stop_qr_scanner()
            st.rerun()
    else:
        # Display check-in screen
        st.header("Attendee Check-in")

        try:
            # Parse the QR code data (assuming it contains a JSON string or an ID)
            qr_data = st.session_state.last_scanned_code

            try:
                # Try to parse as JSON
                attendee_data = json.loads(qr_data)
                attendee_id = attendee_data.get('id', '')
            except:
                # If not JSON, use as plain ID
                attendee_id = qr_data

            st.write(f"Scanned ID: {attendee_id}")

            # Find attendee in the data
            if 'attendees_df' in st.session_state:
                df = st.session_state.attendees_df
                attendee = df[df['ID'].astype(str) == str(attendee_id)]

                if not attendee.empty:
                    st.success("✅ Attendee found!")

                    # Display attendee info
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Attendee Information")
                        for col in attendee.columns:
                            if col not in ['Checked In', 'Check-in Time']:
                                st.write(f"**{col}:** {attendee[col].values[0]}")

                    with col2:
                        st.subheader("Check-in Status")
                        already_checked_in = attendee['Checked In'].values[0] == 'Yes'

                        if already_checked_in:
                            st.warning("⚠️ This attendee has already checked in!")
                            check_in_time = attendee['Check-in Time'].values[0]
                            st.write(f"Previous check-in: {check_in_time}")

                            if st.button("Check in Again"):
                                if update_attendance(sheet_url, attendee_id):
                                    st.balloons()

                                    # Update counters
                                    ticket_type = attendee['Ticket Type'].values[0]
                                    if ticket_type.lower() == 'type a':
                                        st.session_state.type_a_count += 1
                                    elif ticket_type.lower() == 'type b':
                                        st.session_state.type_b_count += 1

                                    time.sleep(2)  # Give time to see the result
                                    st.session_state.scan_mode = True
                                    st.rerun()
                        else:
                            if st.button("Confirm Check-in"):
                                if update_attendance(sheet_url, attendee_id):
                                    st.session_state.checked_in_attendees += 1

                                    # Update ticket type counts
                                    ticket_type = attendee['Ticket Type'].values[0]
                                    if ticket_type.lower() == 'type a':
                                        st.session_state.type_a_count += 1
                                    elif ticket_type.lower() == 'type b':
                                        st.session_state.type_b_count += 1

                                    st.balloons()
                                    time.sleep(2)  # Give time to see the result
                                    st.session_state.scan_mode = True
                                    st.rerun()
                else:
                    st.error("❌ Attendee not found!")
                    if st.button("Scan Again"):
                        st.session_state.scan_mode = True
                        st.rerun()
            else:
                st.error("Attendee data not loaded. Please load attendee data first.")
                if st.button("Load Data and Try Again"):
                    # Attempt to load data
                    df = load_attendee_data(sheet_url)
                    if not df.empty:
                        st.session_state.attendees_df = df
                        st.rerun()
                    else:
                        st.error("Failed to load attendee data.")

        except Exception as e:
            st.error(f"Error processing check-in: {e}")
            if st.button("Try Again"):
                st.session_state.scan_mode = True
                st.rerun()

    # Footer
    st.markdown("---")
    st.caption("Event Check-in System | Powered by Streamlit")

if __name__ == "__main__":
    main()
