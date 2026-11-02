import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Empty, Select, Spin, Table, Tabs, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useNavigate } from "react-router-dom";
import api, { requireItems } from "../../shared/api/client";
import type { Section, Semester } from "../../shared/api/api-types";
import {
  SectionAttendancePage,
  SectionGradebookPage,
} from "./AcademicRecordsPages";
import { useAuth } from "../auth/AuthContext";

interface SectionStudent {
  id: number;
  studentCode: string;
  fullName: string;
  email: string | null;
  cohort: string | null;
  major: string | null;
  registeredAt: string;
}

interface SectionStudentList {
  sectionId: number;
  sectionCode: string;
  currentEnrollment: number;
  maxCapacity: number;
  items: SectionStudent[];
}

interface ItemsResponse<T> {
  items: T[];
}

export function LecturerSectionsPage() {
  const navigate = useNavigate();
  const [semesterId, setSemesterId] = useState<number>();
  const semestersQuery = useQuery({
    queryKey: ["semesters"],
    queryFn: async () => requireItems<Semester>((await api.get<ItemsResponse<Semester>>("/semesters")).data),
  });
  const currentSemesterQuery = useQuery({
    queryKey: ["current-semester"],
    queryFn: async () => (await api.get<Semester>("/semesters/current")).data,
  });
  useEffect(() => {
    if (semesterId === undefined && currentSemesterQuery.data) {
      setSemesterId(currentSemesterQuery.data.id);
    }
  }, [currentSemesterQuery.data, semesterId]);
  const sectionsQuery = useQuery({
    queryKey: ["lecturer-sections", semesterId],
    enabled: semesterId !== undefined,
    queryFn: async () => requireItems<Section>((await api.get<ItemsResponse<Section>>("/lecturers/me/sections", {
      params: { semesterId },
    })).data),
  });

  if (sectionsQuery.isLoading || semestersQuery.isLoading || currentSemesterQuery.isLoading) return <div className="feature-loading"><Spin /></div>;
  if (semestersQuery.isError || currentSemesterQuery.isError) return <Alert type="error" showIcon message="Không tải được học kỳ." />;
  if (sectionsQuery.isError) return <Alert type="error" showIcon message="Không tải được lớp phụ trách." action={<Button size="small" onClick={() => void sectionsQuery.refetch()}>Thử lại</Button>} />;

  return (
    <>
      <div className="feature-toolbar">
        <Select
          aria-label="Học kỳ"
          className="semester-select"
          value={semesterId}
          options={(semestersQuery.data ?? []).map((semester) => ({
            value: semester.id,
            label: `${semester.semesterCode} · ${semester.name}`,
          }))}
          onChange={setSemesterId}
        />
      </div>
      {!sectionsQuery.data?.length ? (
        <div className="feature-empty"><Empty description="Bạn chưa có lớp phụ trách trong học kỳ này." /></div>
      ) : (
        <div className="section-grid">
          {sectionsQuery.data.map((section) => (
            <Card className="section-card" key={section.id}>
              <div className="section-card-top"><span className="section-code">{section.sectionCode}</span><Tag color="blue">{section.semester?.semesterCode ?? "—"}</Tag></div>
              <h3>{section.subject.name}</h3>
              <p className="section-subtitle">{section.subject.subjectCode}</p>
              <Button type="primary" onClick={() => navigate(`/app/sections/${section.id}/students`)}>Danh sách, điểm danh & điểm</Button>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

export function SectionRosterPage({ sectionId }: { sectionId: number }) {
  const { user } = useAuth();
  if (user?.role !== "LECTURER") return <SectionRosterTable sectionId={sectionId} />;

  return (
    <Tabs
      items={[
        { key: "roster", label: "Danh sách sinh viên", children: <SectionRosterTable sectionId={sectionId} /> },
        { key: "attendance", label: "Điểm danh", children: <SectionAttendancePage sectionId={sectionId} /> },
        { key: "grades", label: "Bảng điểm", children: <SectionGradebookPage sectionId={sectionId} /> },
      ]}
    />
  );
}

function SectionRosterTable({ sectionId }: { sectionId: number }) {
  const navigate = useNavigate();
  const rosterQuery = useQuery({
    queryKey: ["section-roster", sectionId],
    queryFn: async () => (await api.get<SectionStudentList>(`/sections/${sectionId}/students`)).data,
  });

  if (rosterQuery.isLoading) return <div className="feature-loading"><Spin /></div>;
  if (rosterQuery.isError) return <Alert type="error" showIcon message="Không tải được danh sách sinh viên của lớp." action={<Button size="small" onClick={() => void rosterQuery.refetch()}>Thử lại</Button>} />;

  const roster = rosterQuery.data;
  const students = roster?.items ?? [];

  const columns: ColumnsType<SectionStudent> = [
    { title: "STT", key: "index", width: 60, align: "center", render: (_, __, i) => i + 1 },
    { title: "MSSV", dataIndex: "studentCode", key: "studentCode", width: 120 },
    { title: "Họ và tên", dataIndex: "fullName", key: "fullName", render: (name: string) => <strong>{name}</strong> },
    { title: "Email", dataIndex: "email", key: "email", render: (val: string | null) => val || "—" },
    { title: "Khóa", dataIndex: "cohort", key: "cohort", width: 90, render: (val: string | null) => val || "—" },
    { title: "Ngành", dataIndex: "major", key: "major", render: (val: string | null) => val || "—" },
    { title: "Thời điểm đăng ký", dataIndex: "registeredAt", key: "registeredAt", width: 180 },
  ];

  return (
    <div className="roster-page">
      <div style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h3 style={{ margin: 0 }}>Lớp học phần: {roster?.sectionCode}</h3>
          <span style={{ color: "#6c757d" }}>Sĩ số hiện tại: <strong>{roster?.currentEnrollment}</strong> / {roster?.maxCapacity} sinh viên</span>
        </div>
        <Button onClick={() => navigate(-1)}>Quay lại</Button>
      </div>
      <Table<SectionStudent>
        rowKey="id"
        size="small"
        dataSource={students}
        columns={columns}
        pagination={{ pageSize: 15, showTotal: (t) => `Tổng ${t} sinh viên` }}
        locale={{ emptyText: <Empty description="Lớp chưa có sinh viên đăng ký." /> }}
      />
    </div>
  );
}
