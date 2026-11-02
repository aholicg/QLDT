/**
 * TypeScript API definitions generated from contracts/openapi.yaml
 * Hệ thống Quản lý & Đăng ký Học phần (QLDT) - Nhóm 20
 */

// ==========================================
// 1. Core & Common Types
// ==========================================

export type UserRole = "ADMIN" | "LECTURER" | "STUDENT";
export type AccountStatus = "ACTIVE" | "LOCKED";

export interface FieldError {
  field: string;
  message: string;
  type?: "STUDENT" | "ROOM" | "LECTURER" | null;
  sectionA?: string;
  sectionB?: string;
  studentCode?: string;
  dayOfWeek?: number;
  periods?: ConflictRange;
  weeks?: ConflictRange;
}

export interface ErrorResponse {
  status: number;
  error: string;
  message: string;
  details: FieldError[];
  path: string;
  timestamp: string;
}

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface HTTPValidationError {
  detail?: ValidationError[];
}

export interface ItemList<T> {
  items: T[];
}

export interface Page<T> {
  items: T[];
  page: number;
  size: number;
  totalItems: number;
  totalPages: number;
}

// ==========================================
// 2. Authentication (UC001)
// ==========================================

export interface LoginRequest {
  username: string;
  password: string;
}

export interface UserInfo {
  userId: number;
  username: string;
  fullName: string;
  email: string | null;
  role: UserRole;
  studentCode: string | null;
  lecturerCode: string | null;
}

export interface CurrentUserResponse {
  user: UserInfo;
}

export interface AuthResponse {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
  user: UserInfo;
}

// ==========================================
// 3. Catalog - References & Lookups
// ==========================================

export interface SemesterRef {
  id: number;
  semesterCode: string;
  name: string;
}

export interface SubjectRef {
  id: number;
  subjectCode: string;
  name: string;
  credits: number;
}

export interface LecturerRef {
  id: number;
  lecturerCode: string;
  fullName: string;
}

export interface RoomRef {
  id: number;
  roomCode: string;
  building: string | null;
  capacity: number;
}

export interface Semester {
  id: number;
  semesterCode: string;
  name: string;
  startDate: string; // YYYY-MM-DD
  endDate: string; // YYYY-MM-DD
  numWeeks: number;
}

export interface CurrentSemester extends Semester {
  currentWeek: number | null;
}

export interface Lookups {
  subjects: SubjectRef[];
  lecturers: LecturerRef[];
  rooms: RoomRef[];
  semesters: Semester[];
}

// ==========================================
// 4. Catalog - Subjects (UC002)
// ==========================================

export interface Subject {
  id: number;
  subjectCode: string;
  name: string;
  credits: number;
  description: string | null;
  sectionCount: number;
}

export interface SubjectCreateRequest {
  subjectCode: string;
  name: string;
  credits: number;
  description?: string | null;
}

export interface SubjectUpdateRequest {
  name: string;
  credits: number;
  description?: string | null;
}

// ==========================================
// 5. Catalog - Course Sections (UC002)
// ==========================================

export interface Section {
  id: number;
  sectionCode: string;
  subject: SubjectRef;
  semester: SemesterRef;
  lecturer: LecturerRef;
  room: RoomRef;
  dayOfWeek: number; // 2 = Thứ 2 .. 8 = Chủ nhật
  startPeriod: number; // 1 .. 12
  endPeriod: number; // 1 .. 12
  startWeek: number;
  endWeek: number;
  maxCapacity: number;
  currentEnrollment: number;
  remainingSeats: number;
  full: boolean;
  registeredByMe?: boolean | null; // chỉ có giá trị khi vai trò là STUDENT
}

export interface SectionCreateRequest {
  subjectId: number;
  semesterId: number;
  lecturerId: number;
  roomId: number;
  dayOfWeek: number;
  startPeriod: number;
  endPeriod: number;
  startWeek: number;
  endWeek: number;
  maxCapacity: number;
  sectionCode: string;
}

export interface SectionUpdateRequest {
  subjectId: number;
  semesterId: number;
  lecturerId: number;
  roomId: number;
  dayOfWeek: number;
  startPeriod: number;
  endPeriod: number;
  startWeek: number;
  endWeek: number;
  maxCapacity: number;
}

export interface SectionStudent {
  id: number;
  studentCode: string;
  fullName: string;
  email: string | null;
  cohort: string | null;
  major: string | null;
  registeredAt: string; // ISO 8601 with +07:00
}

export interface SectionStudentList {
  sectionId: number;
  sectionCode: string;
  currentEnrollment: number;
  maxCapacity: number;
  items: SectionStudent[];
}

// ==========================================
// 6. Registration (UC005, UC006)
// ==========================================

export interface RegisterRequest {
  sectionId: number;
}

export interface ChangeSectionRequest {
  newSectionId: number;
}

export interface Registration {
  id: number;
  registeredAt: string; // ISO 8601 with +07:00
  section: Section;
}

// ==========================================
// 7. Timetable (UC007, UC008)
// ==========================================

export interface TimetableItem {
  sectionId: number;
  sectionCode: string;
  subjectCode: string;
  subjectName: string;
  dayOfWeek: number;
  date: string; // YYYY-MM-DD
  startPeriod: number;
  endPeriod: number;
  roomCode: string;
  lecturerName: string;
  startWeek: number;
  endWeek: number;
}

export interface Timetable {
  semesterId: number;
  week: number;
  weekStartDate: string; // YYYY-MM-DD
  weekEndDate: string; // YYYY-MM-DD
  items: TimetableItem[];
}

// ==========================================
// 8. Attendance and gradebook
// ==========================================

export type AttendanceStatus = "PRESENT" | "ABSENT" | "LATE" | "EXCUSED";

export interface AttendanceEntry {
  studentId: number;
  studentCode: string;
  fullName: string;
  email: string | null;
  status: AttendanceStatus | null;
}

export interface AttendanceSheet {
  sectionId: number;
  sectionCode: string;
  classDate: string;
  scheduledDates: string[];
  items: AttendanceEntry[];
}

export interface AttendanceUpdateItem {
  studentId: number;
  status: AttendanceStatus;
}

export interface AttendanceUpdateRequest {
  classDate: string;
  items: AttendanceUpdateItem[];
}

export interface GradeComponent {
  id: number;
  name: string;
  weightPercentage: number;
  maxScore: number;
  sortOrder: number;
}

export interface GradeComponentInput {
  name: string;
  weightPercentage: number;
  maxScore: number;
}

export interface GradeComponentsRequest {
  items: GradeComponentInput[];
}

export interface StudentGradeRow {
  studentId: number;
  studentCode: string;
  fullName: string;
  email: string | null;
  scores: Record<number, number | null>;
  finalScore: number | null;
}

export interface GradeBook {
  sectionId: number;
  sectionCode: string;
  components: GradeComponent[];
  items: StudentGradeRow[];
}

export interface GradeUpdateItem {
  studentId: number;
  scores: Record<number, number | null>;
}

export interface GradeUpdateRequest {
  items: GradeUpdateItem[];
export interface ConflictRange {
  start: number;
  end: number;
}

export interface ScheduleConflict {
  type: "STUDENT" | "LECTURER" | "ROOM";
  sectionA: string;
  sectionB: string;
  dayOfWeek: number;
  periods: ConflictRange;
  weeks: ConflictRange;
  field?: string;
  studentCode?: string;
  message?: string;
}

export type Conflict = ScheduleConflict;

export interface ScheduleSlot {
  sectionCode?: string | null;
  dayOfWeek: number;
  startPeriod: number;
  endPeriod: number;
  startWeek?: number;
  endWeek?: number;
  roomId?: number | null;
  lecturerId?: number | null;
}

export interface TimetableSuggestion {
  [key: string]: unknown;
}

export interface TimetableSuggestions {
  items: TimetableSuggestion[];
}

// ==========================================
// 8. Tuition and Receipts
// ==========================================

export type InvoiceStatus = "UNPAID" | "PARTIALLY_PAID" | "PAID" | "CANCELLED";

export interface TuitionRate {
  id: number;
  semesterId: number;
  cohort: string | null;
  major: string | null;
  effectiveFrom: string;
  effectiveTo: string | null;
  pricePerCredit: number;
  description: string | null;
  createdAt: string;
}

export interface TuitionRateCreateRequest {
  semesterId: number;
  cohort?: string | null;
  major?: string | null;
  effectiveFrom?: string | null;
  effectiveTo?: string | null;
  pricePerCredit: number;
  description?: string | null;
}

export type TuitionRateUpdateRequest = Omit<TuitionRateCreateRequest, "semesterId">;

export interface TuitionDiscount {
  id: number;
  studentId: number;
  studentCode: string | null;
  studentName: string | null;
  semesterId: number;
  discountPercent: number;
  fixedAmount: number;
  reason: string;
  grantedBy: string;
  createdAt: string;
}

export interface TuitionDiscountCreateRequest {
  studentId?: number | null;
  studentCode?: string | null;
  semesterId: number;
  discountPercent?: number;
  fixedAmount?: number;
  reason: string;
}

export interface TuitionInstallment {
  id: number;
  semesterId: number;
  installmentOrder: number;
  name: string;
  dueDate: string;
  percentage: number | null;
  fixedAmount: number | null;
  allocatedAmount?: number | null;
  status?: "PENDING" | "PAID" | "OVERDUE" | null;
}

export type TuitionInstallmentConfig =
  | {
      installmentOrder: number;
      name: string;
      dueDate: string;
      percentage: number;
      fixedAmount?: null;
    }
  | {
      installmentOrder: number;
      name: string;
      dueDate: string;
      percentage?: null;
      fixedAmount: number;
    };

export interface TuitionInstallmentsPutRequest {
  semesterId: number;
  installments: TuitionInstallmentConfig[];
}

export interface TuitionInvoiceItem {
  id: number;
  subjectId: number;
  subjectCode: string;
  subjectName: string;
  credits: number;
  tuitionCredits: number;
  pricePerCredit: number;
  amount: number;
}

export interface TuitionPayment {
  id: number;
  amount: number;
  idempotencyKey: string;
  paymentMethod: string;
  paidAt: string;
  receiptNo: string | null;
}

export interface TuitionInvoice {
  id: number;
  studentId: number;
  studentCode?: string | null;
  studentName?: string | null;
  cohort?: string | null;
  major?: string | null;
  semesterId: number;
  semesterCode?: string | null;
  totalTuition: number;
  totalDiscount: number;
  amountDue: number;
  amountPaid: number;
  balance: number;
  status: InvoiceStatus;
  isStale: boolean;
  items?: TuitionInvoiceItem[];
  discounts?: TuitionDiscount[];
  installments?: TuitionInstallment[];
  payments?: TuitionPayment[];
  createdAt: string;
  updatedAt: string;
}

export interface PaymentCreateRequest {
  installmentId?: number | null;
  amount: number;
  idempotencyKey: string;
}

export interface Receipt {
  id: number;
  receiptNo: string;
  paymentId: number;
  studentId: number;
  studentCode: string | null;
  studentName: string | null;
  invoiceId: number;
  amount: number;
  amountInWords: string | null;
  issuedAt: string;
  receiptData: Record<string, unknown>;
}

export interface InvoiceGenerateRequest {
  semesterId: number;
  studentId?: number | null;
}

export interface InvoiceGenerateResult {
  totalGenerated: number;
  totalSkipped: number;
  message: string;
}

export interface TuitionSummary {
  semesterId: number;
  semesterCode: string | null;
  totalInvoices: number;
  totalAmountDue: number;
  totalAmountPaid: number;
  totalBalance: number;
  paidCount: number;
  partiallyPaidCount: number;
  unpaidCount: number;
}
