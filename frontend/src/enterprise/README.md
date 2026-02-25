# Frontend Enterprise Module

Path: `frontend/src/enterprise`

## Purpose
- Multi-tenant enterprise UI scaffolding.
- Role-based navigation and action controls.
- Local storage data mode (no enterprise database or JWT backend required).
- Login entry route: `/enterprise/login`.

## Key Files
- `services/localStore.js`: enterprise local storage state for orgs/users/transactions/audit.
- `auth/sessionStore.js`: token/user/org session state.
- `rbac/permissions.js`: role/permission matrix + menu visibility.
- `services/*Api.js`: local-storage-backed service wrappers.
- `pages/*`: dashboard/admin/audit/transactions scaffolds.

## Integration Example
```jsx
import { getTransactions } from "./enterprise/services/transactionsApi";

const response = await getTransactions({ page: 1, page_size: 20, risk_min: 60 });
console.log(response.items);
```

## Theme
This module uses the same existing CSS variables (`--bg`, `--card`, `--text`, `--muted`, etc.) and is compatible with light/dark/vibrant modes.
