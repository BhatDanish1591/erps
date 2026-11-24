import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from '@mui/material'
import { BulkImportResult, studentsApi } from '../../api/students'

interface BulkImportStudentsModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export const BulkImportStudentsModal: React.FC<BulkImportStudentsModalProps> = ({
  open,
  onClose,
  onSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<BulkImportResult | null>(null)

  const handleDownloadTemplate = () => {
    const csvHeader =
      'full_name,email,phone,admission_number,class,section,roll_number,gender,parent_name,parent_phone,city,state\n'
    const sampleRow1 =
      'Aarav Sharma,aarav@example.com,9876543210,,Class 10,A,101,MALE,Rajesh Sharma,9876543211,Mumbai,Maharashtra\n'
    const sampleRow2 =
      'Priya Patel,priya@example.com,9876543212,,Class 10,B,102,FEMALE,Suresh Patel,9876543213,Ahmedabad,Gujarat\n'
    const blob = new Blob([csvHeader + sampleRow1 + sampleRow2], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'student_bulk_import_template.csv')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setError(null)
      setResult(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a CSV file to upload.')
      return
    }

    try {
      setUploading(true)
      setError(null)
      const res = await studentsApi.bulkImport(file)
      setResult(res)
      if (res.successful > 0) {
        onSuccess()
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to process bulk import CSV file.')
    } finally {
      setUploading(false)
    }
  }

  const handleReset = () => {
    setFile(null)
    setResult(null)
    setError(null)
    onClose()
  }

  return (
    <Dialog open={open} onClose={handleReset} maxWidth="md" fullWidth>
      <DialogTitle sx={{ fontWeight: 700 }}>
        Bulk Import Students (CSV)
        <Typography variant="body2" color="text.secondary">
          Upload an Excel-compatible CSV file to register multiple students in batches with automatic quota checks.
        </Typography>
      </DialogTitle>

      <DialogContent sx={{ minHeight: 320 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Step 1: Download Template */}
        <Box
          sx={{
            p: 2,
            mb: 2.5,
            bgcolor: 'action.hover',
            borderRadius: 1.5,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              Need the correct format?
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Download our ready-to-use CSV template with sample student records.
            </Typography>
          </Box>
          <Button variant="outlined" size="small" onClick={handleDownloadTemplate}>
            Download Template
          </Button>
        </Box>

        {/* Step 2: Select File */}
        {!result && (
          <Box
            sx={{
              border: '2px dashed',
              borderColor: file ? 'primary.main' : 'divider',
              borderRadius: 2,
              p: 4,
              textAlign: 'center',
              bgcolor: file ? 'action.selected' : 'background.paper',
            }}
          >
            <input
              type="file"
              accept=".csv,text/csv"
              id="csv-file-input"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />
            <label htmlFor="csv-file-input">
              <Button variant="contained" component="span" disabled={uploading}>
                Select CSV File
              </Button>
            </label>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
              {file ? `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)` : 'Only .csv files supported'}
            </Typography>
          </Box>
        )}

        {/* Step 3: Result Summary */}
        {result && (
          <Box sx={{ mt: 1 }}>
            <Alert
              severity={result.failed === 0 ? 'success' : 'warning'}
              sx={{ mb: 2 }}
            >
              Batch processed: {result.total_processed} total | {result.successful} admitted | {result.failed} failed.
            </Alert>

            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <Chip label={`Total: ${result.total_processed}`} />
              <Chip label={`Successful: ${result.successful}`} color="success" />
              <Chip label={`Failed: ${result.failed}`} color={result.failed > 0 ? 'error' : 'default'} />
            </Box>

            {result.errors.length > 0 && (
              <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 220 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Row</TableCell>
                      <TableCell>Student</TableCell>
                      <TableCell>Reason for Failure</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {result.errors.map((err, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{err.row}</TableCell>
                        <TableCell>{err.name || '—'}</TableCell>
                        <TableCell sx={{ color: 'error.main' }}>{err.error}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2.5 }}>
        <Button onClick={handleReset} disabled={uploading}>
          {result ? 'Done' : 'Cancel'}
        </Button>
        {!result && (
          <Button
            variant="contained"
            onClick={handleUpload}
            disabled={!file || uploading}
            startIcon={uploading ? <CircularProgress size={16} color="inherit" /> : null}
          >
            {uploading ? 'Processing Import...' : 'Import Students'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  )
}
