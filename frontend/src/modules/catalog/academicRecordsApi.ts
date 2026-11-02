import api from "../../shared/api/client";
import type {
  AttendanceSheet,
  AttendanceUpdateRequest,
  GradeBook,
  GradeComponent,
  GradeComponentsRequest,
  GradeUpdateRequest,
  ItemList,
} from "../../shared/api/api-types";

export async function fetchAttendanceSheet(
  sectionId: number,
  classDate?: string,
): Promise<AttendanceSheet> {
  return (
    await api.get<AttendanceSheet>(`/sections/${sectionId}/attendance`, {
      params: classDate ? { classDate } : undefined,
    })
  ).data;
}

export async function saveAttendance(
  sectionId: number,
  request: AttendanceUpdateRequest,
): Promise<AttendanceSheet> {
  return (await api.put<AttendanceSheet>(`/sections/${sectionId}/attendance`, request)).data;
}

export async function fetchGradeBook(sectionId: number): Promise<GradeBook> {
  return (await api.get<GradeBook>(`/sections/${sectionId}/grades`)).data;
}

export async function saveGradeBook(
  sectionId: number,
  request: GradeUpdateRequest,
): Promise<GradeBook> {
  return (await api.put<GradeBook>(`/sections/${sectionId}/grades`, request)).data;
}

export async function fetchGradeComponents(sectionId: number): Promise<GradeComponent[]> {
  return (
    await api.get<ItemList<GradeComponent>>(`/sections/${sectionId}/grade-components`)
  ).data.items;
}

export async function updateGradeComponents(
  sectionId: number,
  request: GradeComponentsRequest,
): Promise<GradeComponent[]> {
  return (
    await api.put<ItemList<GradeComponent>>(
      `/sections/${sectionId}/grade-components`,
      request,
    )
  ).data.items;
}

export async function downloadAcademicReport(
  sectionId: number,
  report: "attendance" | "grades",
): Promise<void> {
  const response = await api.get<Blob>(`/sections/${sectionId}/exports/${report}`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${report === "attendance" ? "diem-danh" : "bang-diem"}-lop-${sectionId}.xlsx`;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
