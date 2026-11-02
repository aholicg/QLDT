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
}
