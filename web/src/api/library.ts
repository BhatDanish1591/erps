import apiClient from './client'

export interface LibraryCategory {
  id: string
  tenant_id: string
  name: string
  code: string
  description?: string
  created_at: string
}

export interface LibraryBookCopy {
  id: string
  tenant_id: string
  book_id: string
  accession_number: string
  status: 'AVAILABLE' | 'ISSUED' | 'LOST' | 'DAMAGED' | 'RESERVED'
  condition_notes?: string
  created_at: string
}

export interface LibraryBook {
  id: string
  tenant_id: string
  category_id: string
  title: string
  author: string
  isbn?: string
  publisher?: string
  edition?: string
  publication_year?: number
  total_copies: number
  available_copies: number
  shelf_location?: string
  description?: string
  cover_image_url?: string
  category_name?: string
  created_at: string
}

export interface BookIssueRequest {
  copy_id: string
  borrower_user_id: string
  borrower_type: 'STUDENT' | 'TEACHER' | 'STAFF'
  student_id?: string
  teacher_id?: string
  due_days?: number
  notes?: string
}

export interface BookReturnRequest {
  copy_id: string
  fine_amount?: number
  fine_paid?: boolean
  condition_notes?: string
}

export interface LibraryBorrowRecord {
  id: string
  tenant_id: string
  copy_id: string
  book_id: string
  book_title?: string
  accession_number?: string
  borrower_type: string
  borrower_name?: string
  issue_date: string
  due_date: string
  return_date?: string
  status: 'ISSUED' | 'RETURNED' | 'OVERDUE' | 'LOST'
  fine_amount: number
  fine_paid: boolean
  notes?: string
  created_at: string
}

export interface LibraryReport {
  total_books: number
  total_copies: number
  available_copies: number
  issued_copies: number
  overdue_copies: number
  total_fines_collected: number
  pending_fines: number
}

export const libraryApi = {
  // Categories
  listCategories: async (): Promise<LibraryCategory[]> => {
    const res = await apiClient.get<LibraryCategory[]>('/library/categories')
    return res.data
  },
  createCategory: async (data: { name: string; code: string; description?: string }): Promise<LibraryCategory> => {
    const res = await apiClient.post<LibraryCategory>('/library/categories', data)
    return res.data
  },

  // Books
  listBooks: async (params?: { category_id?: string; search?: string; limit?: number }): Promise<LibraryBook[]> => {
    const res = await apiClient.get<LibraryBook[]>('/library/books', { params })
    return res.data
  },
  getBook: async (bookId: string): Promise<LibraryBook> => {
    const res = await apiClient.get<LibraryBook>(`/library/books/${bookId}`)
    return res.data
  },
  createBook: async (data: {
    category_id: string
    title: string
    author: string
    isbn?: string
    publisher?: string
    edition?: string
    publication_year?: number
    total_copies?: number
    shelf_location?: string
    description?: string
    cover_image_url?: string
    accession_numbers?: string[]
  }): Promise<LibraryBook> => {
    const res = await apiClient.post<LibraryBook>('/library/books', data)
    return res.data
  },
  listBookCopies: async (bookId: string): Promise<LibraryBookCopy[]> => {
    const res = await apiClient.get<LibraryBookCopy[]>(`/library/books/${bookId}/copies`)
    return res.data
  },

  // Issue & Return
  issueBook: async (data: BookIssueRequest): Promise<LibraryBorrowRecord> => {
    const res = await apiClient.post<LibraryBorrowRecord>('/library/issue', data)
    return res.data
  },
  returnBook: async (data: BookReturnRequest): Promise<LibraryBorrowRecord> => {
    const res = await apiClient.post<LibraryBorrowRecord>('/library/return', data)
    return res.data
  },

  // Borrows History
  listBorrows: async (params?: {
    user_id?: string
    student_id?: string
    status?: string
    limit?: number
  }): Promise<LibraryBorrowRecord[]> => {
    const res = await apiClient.get<LibraryBorrowRecord[]>('/library/borrows', { params })
    return res.data
  },

  // Reports
  getReports: async (): Promise<LibraryReport> => {
    const res = await apiClient.get<LibraryReport>('/library/reports/summary')
    return res.data
  },
}
