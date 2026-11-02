import api from "../../shared/api/client";
import type { CurrentSemester, Lookups, Page, Section, SectionCreateRequest, SectionUpdateRequest, Subject, SubjectCreateRequest, SubjectUpdateRequest } from "../../shared/api/api-types";

export async function fetchSubjects(params: { page: number; size: number; keyword?: string }): Promise<Page<Subject>> {
  const response = await api.get<Page<Subject>>("/subjects", {
    params,
  });
  return response.data;
}

export async function fetchLookups(): Promise<Lookups> {
  return (await api.get<Lookups>("/sections/lookups")).data;
}

export async function fetchCurrentSemester(): Promise<CurrentSemester> {
  return (await api.get<CurrentSemester>("/semesters/current")).data;
}

export async function fetchSections(params: {
  semesterId: number;
  page: number;
  size: number;
  keyword?: string;
  unitKeyword?: string;
}): Promise<Page<Section>> {
  return (await api.get<Page<Section>>("/sections", { params })).data;
}

export async function updateSection(sectionId: number, body: SectionUpdateRequest): Promise<Section> {
  return (await api.put<Section>(`/sections/${sectionId}`, body)).data;
}

export async function createSection(body: SectionCreateRequest): Promise<Section> {
  return (await api.post<Section>("/sections", body)).data;
}

export async function deleteSection(sectionId: number): Promise<void> {
  await api.delete(`/sections/${sectionId}`);
}

export async function createSubject(body: SubjectCreateRequest): Promise<Subject> {
  return (await api.post<Subject>("/subjects", body)).data;
}

export async function updateSubject(subjectId: number, body: SubjectUpdateRequest): Promise<Subject> {
  return (await api.put<Subject>(`/subjects/${subjectId}`, body)).data;
}

export async function deleteSubject(subjectId: number): Promise<void> {
  await api.delete(`/subjects/${subjectId}`);
}
