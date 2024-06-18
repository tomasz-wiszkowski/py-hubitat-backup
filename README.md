# Hubitat backup file snapshot tool

Download and manage Hubitat backup files without exposing credentials.

This utility uses Hubitat diagnostic page (http://hubitat:8081) to retrieve 
periodic snapshots. To use this mechanism, snapshots have to be enabled first 
on http://hubitat/hub/backup.

Note that unlike regular access, this utility relies on diagnostic page, where 
the only credential being used is the hub's MAC address. This allows running 
periodic snapshots of the configuration backups without exposing credentials.

## Usage

The tool requires IP address and a MAC address of the device to talk to. In 
order for the tool to work reliably, device must either use a static IP 
address, or respond to mDNS requests.

The MAC address can be acquired from Hubitat's Details page: http://hubitat/hub/
details. 

Once backups are enabled and the IP and MAC addresses are known, simply run:

```
hubitat-backup.py <ip address> <mac address> <destination dir>
```

An optional parameter `-a` / `--max-age-days` can be specified to dictate the 
maximum age of the preserved configuration files (defaults to 90 days).

## Caveats

Please note that Hubitat configuration files follow a rather standard naming 
scheme (`date~version.lzf`). For that reason, keeping backups of multiple 
Hubitat devices mandates using different folders for each device. This utility 
does not re-download snapshots if a local copy is already available, meaning 
your hubs will likely not be backed up in the event of a name conflict.

```
hubitat-backup.py <device 1 ip> <device 1 mac> /path/to/backups/hubitat1
hubitat-backup.py <device 2 ip> <device 2 mac> /path/to/backups/hubitat2
```