import { useState } from 'react'
import { Autocomplete, Box, Dialog, DialogContent, DialogTitle, TextField, Typography } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import type { NavbarModule } from './navbarModules'

export function NavbarSearch({ modules, onClose }: { modules: NavbarModule[]; onClose: () => void }) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [suggestionsOpen, setSuggestionsOpen] = useState(false)
  const options = modules.flatMap((module) => module.items.flatMap((item) =>
    item.path ? [{ label: item.label, section: item.section, path: item.path + (item.search ?? ''), module: module.label }] : [],
  ))

  return (
    <Dialog open onClose={onClose} aria-labelledby="navbar-search-title" fullWidth maxWidth="xs">
      <DialogTitle id="navbar-search-title">Search ERP</DialogTitle>
      <DialogContent sx={{ minHeight: 100, pb: 2 }}>
        <Autocomplete
          autoHighlight
          disablePortal
          open={suggestionsOpen && Boolean(query.trim())}
          inputValue={query}
          onInputChange={(_, value) => {
            setQuery(value)
            setSuggestionsOpen(Boolean(value.trim()))
          }}
          onOpen={() => setSuggestionsOpen(true)}
          onClose={() => setSuggestionsOpen(false)}
          options={options}
          getOptionLabel={(option) => option.label}
          getOptionKey={(option) => `${option.module}/${option.label}`}
          groupBy={(option) => option.module}
          filterOptions={(items, { inputValue }) => {
            const words = inputValue.toLowerCase().trim().split(/\s+/)
            return items.filter((item) => {
              const text = `${item.module} ${item.label} ${item.section ?? ''}`.toLowerCase()
              return words.every((word) => text.includes(word))
            }).slice(0, 18)
          }}
          onChange={(_, option) => {
            if (!option) return
            onClose()
            navigate(option.path)
          }}
          noOptionsText="No accessible pages match your search"
          renderInput={(params) => <TextField {...params} label="Modules and pages" size="small" autoFocus />}
          renderOption={({ key, ...props }, option) => (
            <Box component="li" key={key} {...props} sx={{ flexDirection: 'column', alignItems: 'flex-start !important' }}>
              {option.label}
              {option.section && <Typography variant="caption" color="text.secondary">{option.section}</Typography>}
            </Box>
          )}
          slotProps={{
            popper: { sx: { position: 'static !important', transform: 'none !important', width: '100% !important' } },
            paper: { elevation: 0 },
            listbox: { sx: { maxHeight: 'min(320px, 45dvh)' } },
          }}
        />
      </DialogContent>
    </Dialog>
  )
}
