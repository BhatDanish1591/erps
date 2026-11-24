import { PageHeader } from '@/components/ui/PageHeader'
import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Chip,
  Button,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  MenuItem,
  InputAdornment,
} from '@mui/material'
import MenuBookIcon from '@mui/icons-material/MenuBook'
import AutoStoriesIcon from '@mui/icons-material/AutoStories'
import CategoryIcon from '@mui/icons-material/Category'
import AssignmentReturnIcon from '@mui/icons-material/AssignmentReturn'
import SearchIcon from '@mui/icons-material/Search'
import AddIcon from '@mui/icons-material/Add'

import {
  libraryApi,
  LibraryBook,
  LibraryCategory,
  LibraryBorrowRecord,
  LibraryReport,
  LibraryBookCopy,
} from '../../api/library'

export default function LibraryManagementPage() {
  const [tab, setTab] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Data states
  const [report, setReport] = useState<LibraryReport | null>(null)
  const [books, setBooks] = useState<LibraryBook[]>([])
  const [categories, setCategories] = useState<LibraryCategory[]>([])
  const [borrows, setBorrows] = useState<LibraryBorrowRecord[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')

  // Modals
  const [openBookModal, setOpenBookModal] = useState(false)
  const [openCategoryModal, setOpenCategoryModal] = useState(false)
  const [openIssueModal, setOpenIssueModal] = useState(false)
  const [openReturnModal, setOpenReturnModal] = useState(false)
  const [selectedBookCopies, setSelectedBookCopies] = useState<LibraryBookCopy[]>([])
  const [openCopiesModal, setOpenCopiesModal] = useState(false)

  // Form states
  const [newCategory, setNewCategory] = useState({ name: '', code: '', description: '' })
  const [newBook, setNewBook] = useState({
    title: '',
    author: '',
    category_id: '',
    isbn: '',
    publisher: '',
    edition: '1st',
    total_copies: 1,
    shelf_location: '',
    description: '',
  })
  const [issueForm, setIssueForm] = useState({
    copy_id: '',
    borrower_user_id: '',
    borrower_type: 'STUDENT' as 'STUDENT' | 'TEACHER' | 'STAFF',
    due_days: 14,
    notes: '',
  })
  const [returnForm, setReturnForm] = useState({
    copy_id: '',
    fine_amount: 0,
    fine_paid: false,
    condition_notes: '',
  })

  const loadAll = async () => {
    try {
      setError(null)
      const [repData, catData, bookData, borrowData] = await Promise.all([
        libraryApi.getReports().catch(() => null),
        libraryApi.listCategories().catch(() => []),
        libraryApi.listBooks({ search: searchQuery || undefined, category_id: selectedCategory || undefined }).catch(() => []),
        libraryApi.listBorrows().catch(() => []),
      ])
      setReport(repData)
      setCategories(catData)
      setBooks(bookData)
      setBorrows(borrowData)
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err?.message || 'Failed to load library data')
    }
  }

  useEffect(() => {
    loadAll()
  }, [selectedCategory])

  const handleSearch = () => {
    libraryApi.listBooks({ search: searchQuery || undefined, category_id: selectedCategory || undefined })
      .then(setBooks)
      .catch((err) => setError(err.message))
  }

  const handleCreateCategory = async () => {
    try {
      await libraryApi.createCategory(newCategory)
      setSuccess('Category created successfully')
      setOpenCategoryModal(false)
      setNewCategory({ name: '', code: '', description: '' })
      loadAll()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to create category')
    }
  }

  const handleCreateBook = async () => {
    try {
      await libraryApi.createBook({
        ...newBook,
        total_copies: Number(newBook.total_copies),
      })
      setSuccess('Book added to catalog with copies')
      setOpenBookModal(false)
      loadAll()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to add book')
    }
  }

  const handleViewCopies = async (bookId: string) => {
    try {
      const copies = await libraryApi.listBookCopies(bookId)
      setSelectedBookCopies(copies)
      setOpenCopiesModal(true)
    } catch (err: any) {
      setError('Failed to load copies')
    }
  }

  const handleIssueBook = async () => {
    try {
      await libraryApi.issueBook({
        copy_id: issueForm.copy_id,
        borrower_user_id: issueForm.borrower_user_id,
        borrower_type: issueForm.borrower_type,
        due_days: Number(issueForm.due_days),
        notes: issueForm.notes,
      })
      setSuccess('Book issued successfully')
      setOpenIssueModal(false)
      loadAll()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to issue book')
    }
  }

  const handleReturnBook = async () => {
    try {
      await libraryApi.returnBook({
        copy_id: returnForm.copy_id,
        fine_amount: Number(returnForm.fine_amount),
        fine_paid: returnForm.fine_paid,
        condition_notes: returnForm.condition_notes,
      })
      setSuccess('Book returned successfully')
      setOpenReturnModal(false)
      loadAll()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to return book')
    }
  }

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <PageHeader
          title="Library"
          description="Manage the book catalog, circulation, returns, and fines."
          icon={<MenuBookIcon />}
        >
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <Button variant="outlined" startIcon={<CategoryIcon />} onClick={() => setOpenCategoryModal(true)}>
              New Category
            </Button>
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpenBookModal(true)}>
              Add Book
            </Button>
          </Box>
        </PageHeader>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* KPI Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">Total Titles</Typography>
              <Typography variant="h4" fontWeight="bold">{report?.total_books ?? 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">Total Copies</Typography>
              <Typography variant="h4" fontWeight="bold">{report?.total_copies ?? 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="success.main">Available Copies</Typography>
              <Typography variant="h4" fontWeight="bold" color="success.main">
                {report?.available_copies ?? 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="warning.main">Issued / Overdue</Typography>
              <Typography variant="h4" fontWeight="bold" color="warning.main">
                {report?.issued_copies ?? 0} / {report?.overdue_copies ?? 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">Fines Collected</Typography>
              <Typography variant="h4" fontWeight="bold">
                ₹{report?.total_fines_collected ?? '0.00'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Navigation Tabs */}
      <Tabs value={tab} onChange={(_, val) => setTab(val)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tab icon={<AutoStoriesIcon />} iconPosition="start" label="Catalog & Inventory" />
        <Tab icon={<AssignmentReturnIcon />} iconPosition="start" label="Issue & Return History" />
        <Tab icon={<CategoryIcon />} iconPosition="start" label="Book Categories" />
      </Tabs>

      {/* Tab 0: Catalog & Inventory */}
      {tab === 0 && (
        <Box>
          <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
            <TextField
              size="small"
              placeholder="Search by title, author, or ISBN..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              sx={{ flexGrow: 1 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
            <TextField
              size="small"
              select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              sx={{ width: 220 }}
              label="Filter Category"
            >
              <MenuItem value="">All Categories</MenuItem>
              {categories.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.name}
                </MenuItem>
              ))}
            </TextField>
            <Button variant="outlined" onClick={handleSearch}>
              Search
            </Button>
          </Box>

          <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
            <Table sx={{ minWidth: 600 }}>
              <TableHead>
                <TableRow sx={{ backgroundColor: 'action.hover' }}>
                  <TableCell>Title</TableCell>
                  <TableCell>Author</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell>Shelf Location</TableCell>
                  <TableCell align="center">Total</TableCell>
                  <TableCell align="center">Available</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {books.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                      No books found. Add books to the catalog to get started.
                    </TableCell>
                  </TableRow>
                ) : (
                  books.map((b) => (
                    <TableRow key={b.id} hover>
                      <TableCell>
                        <Typography fontWeight="medium">{b.title}</Typography>
                        {b.isbn && (
                          <Typography variant="caption" color="text.secondary">
                            ISBN: {b.isbn}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>{b.author}</TableCell>
                      <TableCell>
                        <Chip size="small" label={b.category_name || 'General'} />
                      </TableCell>
                      <TableCell>{b.shelf_location || '-'}</TableCell>
                      <TableCell align="center">{b.total_copies}</TableCell>
                      <TableCell align="center">
                        <Chip
                          size="small"
                          color={b.available_copies > 0 ? 'success' : 'default'}
                          label={`${b.available_copies} available`}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Button size="small" onClick={() => handleViewCopies(b.id)}>
                          View Copies
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* Tab 1: Borrow Records */}
      {tab === 1 && (
        <Box>
          <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
            <Table sx={{ minWidth: 600 }}>
              <TableHead>
                <TableRow sx={{ backgroundColor: 'action.hover' }}>
                  <TableCell>Book Title</TableCell>
                  <TableCell>Barcode / Accession</TableCell>
                  <TableCell>Borrower</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell>Issue Date</TableCell>
                  <TableCell>Due Date</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Fine</TableCell>
                  <TableCell align="right">Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {borrows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                      No borrow records found.
                    </TableCell>
                  </TableRow>
                ) : (
                  borrows.map((r) => (
                    <TableRow key={r.id} hover>
                      <TableCell sx={{ fontWeight: 'medium' }}>{r.book_title || '-'}</TableCell>
                      <TableCell>{r.accession_number || '-'}</TableCell>
                      <TableCell>{r.borrower_name || '-'}</TableCell>
                      <TableCell>
                        <Chip size="small" label={r.borrower_type} />
                      </TableCell>
                      <TableCell>{r.issue_date}</TableCell>
                      <TableCell>{r.due_date}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          color={
                            r.status === 'ISSUED'
                              ? 'primary'
                              : r.status === 'RETURNED'
                              ? 'success'
                              : 'error'
                          }
                          label={r.status}
                        />
                      </TableCell>
                      <TableCell>
                        {Number(r.fine_amount) > 0 ? (
                          <Chip
                            size="small"
                            color={r.fine_paid ? 'success' : 'error'}
                            label={`₹${r.fine_amount} ${r.fine_paid ? '(Paid)' : '(Due)'}`}
                          />
                        ) : (
                          '₹0.00'
                        )}
                      </TableCell>
                      <TableCell align="right">
                        {r.status === 'ISSUED' && (
                          <Button
                            size="small"
                            color="success"
                            variant="outlined"
                            onClick={() => {
                              setReturnForm({
                                copy_id: r.copy_id,
                                fine_amount: 0,
                                fine_paid: false,
                                condition_notes: '',
                              })
                              setOpenReturnModal(true)
                            }}
                          >
                            Return
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* Tab 2: Categories */}
      {tab === 2 && (
        <Box>
          <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
            <Table sx={{ minWidth: 600 }}>
              <TableHead>
                <TableRow sx={{ backgroundColor: 'action.hover' }}>
                  <TableCell>Category Name</TableCell>
                  <TableCell>Code</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell>Created At</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {categories.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell sx={{ fontWeight: 'medium' }}>{c.name}</TableCell>
                    <TableCell>
                      <code>{c.code}</code>
                    </TableCell>
                    <TableCell>{c.description || '-'}</TableCell>
                    <TableCell>{new Date(c.created_at).toLocaleDateString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* Dialog: Create Category */}
      <Dialog open={openCategoryModal} onClose={() => setOpenCategoryModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Book Category</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField
            label="Category Name"
            value={newCategory.name}
            onChange={(e) => setNewCategory({ ...newCategory, name: e.target.value })}
            fullWidth
            required
          />
          <TextField
            label="Category Code"
            value={newCategory.code}
            onChange={(e) => setNewCategory({ ...newCategory, code: e.target.value.toUpperCase() })}
            placeholder="e.g. COMP-SCI"
            fullWidth
            required
          />
          <TextField
            label="Description"
            value={newCategory.description}
            onChange={(e) => setNewCategory({ ...newCategory, description: e.target.value })}
            multiline
            rows={3}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCategoryModal(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateCategory} disabled={!newCategory.name || !newCategory.code}>
            Save Category
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: Add Book */}
      <Dialog open={openBookModal} onClose={() => setOpenBookModal(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add New Book to Catalog</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={8}>
              <TextField
                label="Book Title"
                value={newBook.title}
                onChange={(e) => setNewBook({ ...newBook, title: e.target.value })}
                fullWidth
                required
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                select
                label="Category"
                value={newBook.category_id}
                onChange={(e) => setNewBook({ ...newBook, category_id: e.target.value })}
                fullWidth
                required
              >
                {categories.map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.name}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Author"
                value={newBook.author}
                onChange={(e) => setNewBook({ ...newBook, author: e.target.value })}
                fullWidth
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="ISBN"
                value={newBook.isbn}
                onChange={(e) => setNewBook({ ...newBook, isbn: e.target.value })}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Total Copies"
                type="number"
                value={newBook.total_copies}
                onChange={(e) => setNewBook({ ...newBook, total_copies: Number(e.target.value) })}
                fullWidth
                inputProps={{ min: 1 }}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Edition"
                value={newBook.edition}
                onChange={(e) => setNewBook({ ...newBook, edition: e.target.value })}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Shelf Location"
                value={newBook.shelf_location}
                onChange={(e) => setNewBook({ ...newBook, shelf_location: e.target.value })}
                placeholder="e.g. Row 3, Rack A"
                fullWidth
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenBookModal(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreateBook}
            disabled={!newBook.title || !newBook.author || !newBook.category_id}
          >
            Add Book
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: View Copies */}
      <Dialog open={openCopiesModal} onClose={() => setOpenCopiesModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Physical Book Copies</DialogTitle>
        <DialogContent>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Accession Number</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {selectedBookCopies.map((cp) => (
                  <TableRow key={cp.id}>
                    <TableCell>
                      <code>{cp.accession_number}</code>
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        color={cp.status === 'AVAILABLE' ? 'success' : 'default'}
                        label={cp.status}
                      />
                    </TableCell>
                    <TableCell align="right">
                      {cp.status === 'AVAILABLE' && (
                        <Button
                          size="small"
                          variant="contained"
                          onClick={() => {
                            setIssueForm({ ...issueForm, copy_id: cp.id })
                            setOpenCopiesModal(false)
                            setOpenIssueModal(true)
                          }}
                        >
                          Issue
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCopiesModal(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: Issue Book */}
      <Dialog open={openIssueModal} onClose={() => setOpenIssueModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Issue Book Copy</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField
            select
            label="Borrower Role"
            value={issueForm.borrower_type}
            onChange={(e: any) => setIssueForm({ ...issueForm, borrower_type: e.target.value })}
            fullWidth
          >
            <MenuItem value="STUDENT">Student</MenuItem>
            <MenuItem value="TEACHER">Teacher</MenuItem>
            <MenuItem value="STAFF">Staff</MenuItem>
          </TextField>
          <TextField
            label="Borrower User ID (UUID)"
            value={issueForm.borrower_user_id}
            onChange={(e) => setIssueForm({ ...issueForm, borrower_user_id: e.target.value })}
            fullWidth
            required
            helperText="Enter the UUID of the enrolled student or staff"
          />
          <TextField
            label="Lending Duration (Days)"
            type="number"
            value={issueForm.due_days}
            onChange={(e) => setIssueForm({ ...issueForm, due_days: Number(e.target.value) })}
            fullWidth
          />
          <TextField
            label="Notes"
            value={issueForm.notes}
            onChange={(e) => setIssueForm({ ...issueForm, notes: e.target.value })}
            multiline
            rows={2}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenIssueModal(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleIssueBook} disabled={!issueForm.borrower_user_id}>
            Confirm Issue
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: Return Book */}
      <Dialog open={openReturnModal} onClose={() => setOpenReturnModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Process Book Return</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField
            label="Late Fine Amount (₹)"
            type="number"
            value={returnForm.fine_amount}
            onChange={(e) => setReturnForm({ ...returnForm, fine_amount: Number(e.target.value) })}
            fullWidth
          />
          <TextField
            select
            label="Fine Paid Status"
            value={returnForm.fine_paid ? 'YES' : 'NO'}
            onChange={(e) => setReturnForm({ ...returnForm, fine_paid: e.target.value === 'YES' })}
            fullWidth
          >
            <MenuItem value="YES">Paid Immediately</MenuItem>
            <MenuItem value="NO">Pending / Unpaid</MenuItem>
          </TextField>
          <TextField
            label="Condition Notes"
            value={returnForm.condition_notes}
            onChange={(e) => setReturnForm({ ...returnForm, condition_notes: e.target.value })}
            placeholder="e.g. Good condition, pages intact"
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenReturnModal(false)}>Cancel</Button>
          <Button variant="contained" color="success" onClick={handleReturnBook}>
            Confirm Return
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
