# Dataset Notes

Mine currently focuses on four productized dataset families:

- Wikipedia
- arXiv
- Amazon
- LinkedIn

## Runtime behavior

- first run can require dataset selection
- selected datasets shape discovery scheduling
- dataset cooldowns apply after `429`
- occupancy and preflight checks run before submit
