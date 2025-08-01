import requests
import json
import tkinter as tk
from tkinter import messagebox

# GLPI API endpoint and authentication tokens

GLPI_URL = "API URL" # GLPI API URL
APP_TOKEN = "TOKEN" #SOC API Token
USER_TOKEN = "TOKEN" #Post Only User Token


def get_session_token():
    """Authenticate with the GLPI API and retrieve a session token."""
    headers = {"App-Token": APP_TOKEN}
    data = {"user_token": USER_TOKEN}
    r = requests.post(f"{GLPI_URL}/initSession", headers=headers, json=data)
    r.raise_for_status()
    return r.json()["session_token"]

def find_tickets(session_token, field, search_term):
    """Search for existing tickets in GLPI by a given search term."""
    headers = {
        "App-Token": APP_TOKEN,
        "Session-Token": session_token
    }
    params = {
        "criteria[0][field]": field,
        "criteria[0][searchtype]": "contains",
        "criteria[0][value]": search_term
    }
    r = requests.get(f"{GLPI_URL}/search/Ticket", headers=headers, params=params)
    r.raise_for_status()
    return r.json()

def create_ticket(session_token, ticket_name):
    """Create a master ticket in GLPI with the provided name."""
    headers = {
        "App-Token": APP_TOKEN,
        "Session-Token": session_token,
        "Content-Type": "application/json"
    }
    ticket_data = {
        "input": {
            "name": ticket_name,
            "content": f"Master ticket for {ticket_name}",
            "itilcategories_id": 1,
            "urgency": 5,
            "impact": 5,
            "priority": 5,
        }
    }
    r = requests.post(f"{GLPI_URL}/Ticket", headers=headers, data=json.dumps(ticket_data))
    r.raise_for_status()
    return r.json()

def link_tickets(session_token, ticket_id, master_ticket_id):
    """Link two tickets in GLPI as 'Related to'."""
    headers = {
        "App-Token": APP_TOKEN,
        "Session-Token": session_token,
        "Content-Type": "application/json"
    }
    data = {
        "input": {
            "tickets_id_1": ticket_id,
            "tickets_id_2": master_ticket_id,
            "ticketlinks_id": 1  # 1 = "Related to"
        }
    }
    r = requests.post(f"{GLPI_URL}/Ticket_Ticket", headers=headers, data=json.dumps(data))
    r.raise_for_status()
    return r.json()

class TicketLinkerGUI:
    """Tkinter GUI for searching, creating, and linking GLPI tickets."""
    def __init__(self, root):
        self.root = root
        self.root.title("GLPI Ticket Linker")
        self.session_token = None
        self.field_options = {"Name": 1, "Description": 2}

        # Search fields
        tk.Label(root, text="Search Name:").grid(row=0, column=0, sticky="e", padx=(16,4), pady=4)
        self.name_entry = tk.Entry(root, width=30)
        self.name_entry.grid(row=0, column=1, sticky="w", padx=(4,16), pady=4)
        tk.Label(root, text="Search Description:").grid(row=1, column=0, sticky="e", padx=(16,4), pady=4)
        self.desc_entry = tk.Entry(root, width=30)
        self.desc_entry.grid(row=1, column=1, sticky="w", padx=(4,16), pady=4)
        self.search_btn = tk.Button(root, text="Search Tickets", command=self.search_tickets)
        self.search_btn.grid(row=2, column=0, columnspan=2, pady=8, padx=8)

        # Results listbox with scrollbar
        self.results_frame = tk.Frame(root)
        self.results_frame.grid(row=3, column=0, columnspan=2, pady=8, padx=8, sticky="nsew")
        self.results_listbox = tk.Listbox(self.results_frame, width=60, selectmode=tk.MULTIPLE)
        self.results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar = tk.Scrollbar(self.results_frame, orient=tk.VERTICAL, command=self.results_listbox.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_listbox.config(yscrollcommand=self.scrollbar.set)

        # Master ticket creation
        tk.Label(root, text="Master Ticket Name:").grid(row=4, column=0, sticky="e", padx=(16,4), pady=4)
        self.master_entry = tk.Entry(root, width=30)
        self.master_entry.grid(row=4, column=1, sticky="w", padx=(4,16), pady=4)
        self.create_master_btn = tk.Button(root, text="Create Master Ticket", command=self.create_master_ticket)
        self.create_master_btn.grid(row=5, column=0, columnspan=2, pady=8, padx=8)

        # Status label
        self.status_label = tk.Label(root, text="", fg="blue", anchor="w", justify="left")
        self.status_label.grid(row=6, column=0, columnspan=2, sticky="ew", padx=8, pady=4)

        self.tickets = []
        self.last_master_ticket_id = None

        # Configure grid expansion
        for i in range(2):
            root.columnconfigure(i, weight=1)
        for i in range(7):
            root.rowconfigure(i, weight=0)
        root.rowconfigure(3, weight=1)
        self.results_frame.rowconfigure(0, weight=1)
        self.results_frame.columnconfigure(0, weight=1)

        self.init_session()

    def init_session(self):
        """Initialize GLPI session and update status."""
        try:
            self.session_token = get_session_token()
            self.status_label.config(text="Session initialized.")
        except Exception as e:
            self.status_label.config(text=f"Session error: {e}")

    def search_tickets(self):
        """Search for tickets by name and/or description and display results."""
        name_term = self.name_entry.get()
        desc_term = self.desc_entry.get()
        self.results_listbox.delete(0, tk.END)
        try:
            params = {}
            idx = 0
            if name_term:
<<<<<<< HEAD
                params[f"criteria[{idx}][field]"] = 1  # Name
=======
                params[f"criteria[{idx}][field]"] = 1
>>>>>>> 0a16eed0dc346ff2982f9d5be8ba7efa72871eff
                params[f"criteria[{idx}][searchtype]"] = "contains"
                params[f"criteria[{idx}][value]"] = name_term
                idx += 1
            if desc_term:
                if idx > 0:
                    params[f"criteria[{idx}][link]"] = "AND"
<<<<<<< HEAD
                # Try all likely field ids for description/content
                # 21: content, 4: description, 12: summary, 15: solution
                # We'll try 21 (content) first, then fallback to 4 if no results
=======
>>>>>>> 0a16eed0dc346ff2982f9d5be8ba7efa72871eff
                params[f"criteria[{idx}][field]"] = 21
                params[f"criteria[{idx}][searchtype]"] = "contains"
                params[f"criteria[{idx}][value]"] = desc_term
                idx += 1
            headers = {
                "App-Token": APP_TOKEN,
                "Session-Token": self.session_token
            }
            params["forcedisplay[0]"] = "id"
            params["forcedisplay[1]"] = "name"
<<<<<<< HEAD
            params["forcedisplay[2]"] = "21"
=======
            params["forcedisplay[2]"] = "2"
>>>>>>> 0a16eed0dc346ff2982f9d5be8ba7efa72871eff
            params["range"] = "0-999"
            r = requests.get(f"{GLPI_URL}/search/Ticket", headers=headers, params=params)
            r.raise_for_status()
            results = r.json()
<<<<<<< HEAD
            # If no results and desc_term was used, try field 4 (description)
            if not results.get("data") and desc_term:
                idx -= 1
                params.pop(f"criteria[{idx}][field]")
                params.pop(f"criteria[{idx}][searchtype]")
                params.pop(f"criteria[{idx}][value]")
                if idx > 0:
                    params.pop(f"criteria[{idx}][link]", None)
                params[f"criteria[{idx}][field]"] = 4
                params[f"criteria[{idx}][searchtype]"] = "contains"
                params[f"criteria[{idx}][value]"] = desc_term
                params["forcedisplay[2]"] = "4"
                r = requests.get(f"{GLPI_URL}/search/Ticket", headers=headers, params=params)
                r.raise_for_status()
                results = r.json()
=======
>>>>>>> 0a16eed0dc346ff2982f9d5be8ba7efa72871eff
            self.tickets = []
            ticket_entries = []
            for t in results.get("data", []):
                ticket_data = t.get("0") if "0" in t else t
<<<<<<< HEAD
                ticket_id = ticket_data.get("id") or t.get("id") or ""
                name = ticket_data.get("name") or t.get("name") or ""
=======
                ticket_id = (
                    ticket_data.get("id")
                    or ticket_data.get("2")
                    or t.get("id")
                    or t.get("2")
                    or ""
                )
                name = (
                    ticket_data.get("name")
                    or ticket_data.get("1")
                    or t.get("name")
                    or t.get("1")
                    or ""
                )
>>>>>>> 0a16eed0dc346ff2982f9d5be8ba7efa72871eff
                if ticket_id:
                    ticket_entries.append({"id": ticket_id, "name": name})
            ticket_entries.sort(key=lambda x: int(x["id"]) if str(x["id"]).isdigit() else x["id"])
            for entry in ticket_entries:
                self.tickets.append(entry)
                display = f"ID: {entry['id']} | Name: {entry['name']}"
                self.results_listbox.insert(tk.END, display)
            if not self.tickets:
                self.status_label.config(text="No tickets found.")
            else:
                self.status_label.config(text=f"Found {len(self.tickets)} tickets.")
        except Exception as e:
            self.status_label.config(text=f"Search error: {e}")

    def create_master_ticket(self):
        """Create a master ticket and link selected tickets to it."""
        name = self.master_entry.get()
        if not name:
            messagebox.showwarning("Input Error", "Please enter a master ticket name.")
            return
        try:
            result = create_ticket(self.session_token, name)
            ticket_id = result.get("id") or result.get("data", {}).get("id")
            self.last_master_ticket_id = ticket_id
            self.status_label.config(text=f"Master ticket created with ID: {ticket_id}")
            selected_indices = self.results_listbox.curselection()
            if not selected_indices:
                tickets_to_link = self.tickets
            else:
                tickets_to_link = [self.tickets[i] for i in selected_indices]
            linked_count = 0
            link_errors = []
            for ticket in tickets_to_link:
                try:
                    tid = ticket["id"]
                    tid_int = int(tid)
                    ticket_id_int = int(ticket_id)
                    headers = {
                        "App-Token": APP_TOKEN,
                        "Session-Token": self.session_token,
                        "Content-Type": "application/json"
                    }
                    data = {
                        "input": {
                            "tickets_id_1": tid_int,
                            "tickets_id_2": ticket_id_int,
                            "ticketlinks_id": 1
                        }
                    }
                    url = f"{GLPI_URL}/Ticket_Ticket"
                    r = requests.post(url, headers=headers, data=json.dumps(data))
                    r.raise_for_status()
                    linked_count += 1
                except Exception as e:
                    link_errors.append(str(e))
            if tickets_to_link:
                msg = f"Master ticket created with ID: {ticket_id}. Linked {linked_count} tickets."
                if link_errors:
                    msg += f" Errors: {'; '.join(link_errors)}"
                self.status_label.config(text=msg)
        except Exception as e:
            self.status_label.config(text=f"Create error: {e}")

def main():
    root = tk.Tk()
    app = TicketLinkerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
<<<<<<< HEAD
    root.mainloop()

if __name__ == "__main__":
    main()
    root.mainloop()

if __name__ == "__main__":
    main()
    root.mainloop()

if __name__ == "__main__":
    main()
=======
>>>>>>> 0a16eed0dc346ff2982f9d5be8ba7efa72871eff
