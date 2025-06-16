IRC Bouncer




```mermaid
graph TD
    subgraph "Internet"
        IRC_Client[Your IRC Client]
        IRC_Network[IRC Network e.g., Libera.Chat]
    end

    subgraph "Your GCP Project"
        VPC[VPC Network]
        subgraph "Firewall"
            FW_SSH[Allow SSH from your IP]
            FW_ZNC[Allow ZNC Port from anywhere]
        end
        subgraph "Compute Engine VM (e2-micro)"
            OS[Debian/Ubuntu OS]
            ZNC_Service[ZNC Application running as a systemd service]
            ZNC_Config[(ZNC Configuration Files)]
        end
    end

    IRC_Client -- Port 6697/YourPort --> FW_ZNC --> ZNC_Service
    ZNC_Service <--> IRC_Network
    ZNC_Service -- reads/writes --> ZNC_Config
    ```
