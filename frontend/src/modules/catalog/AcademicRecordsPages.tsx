import { useEffect, useMemo, useState } from "react";
import { DownloadOutlined, SaveOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  InputNumber,
  Select,
  Space,
  Spin,
  Table,
  Tag,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import type {
  AttendanceEntry,
  AttendanceStatus,
  GradeComponent,
  StudentGradeRow,
} from "../../shared/api/api-types";
import {
  downloadAcademicReport,
  fetchAttendanceSheet,
  fetchGradeBook,
  saveAttendance,
  saveGradeBook,
} from "./academicRecordsApi";

const attendanceLabels: Record<AttendanceStatus, string> = {
  PRESENT: "Có mặt",
  ABSENT: "Vắng",
  LATE: "Muộn",
  EXCUSED: "Có phép",
};

const attendanceOptions = Object.entries(attendanceLabels).map(([value, label]) => ({
  value,
  label,
}));

function statusMap(items: AttendanceEntry[]): Record<number, AttendanceStatus | undefined> {
  const statuses: Record<number, AttendanceStatus | undefined> = {};
  for (const entry of items) {
    if (entry.status !== null) statuses[entry.studentId] = entry.status;
  }
  return statuses;
}

export function SectionAttendancePage({ sectionId }: { sectionId: number }) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [classDate, setClassDate] = useState<string>();
  const [statuses, setStatuses] = useState<Record<number, AttendanceStatus | undefined>>({});
  const attendanceQuery = useQuery({
    queryKey: ["attendance", sectionId, classDate],
    queryFn: () => fetchAttendanceSheet(sectionId, classDate),
  });

  useEffect(() => {
    if (!attendanceQuery.data) return;
    if (!classDate) setClassDate(attendanceQuery.data.classDate);
    setStatuses(statusMap(attendanceQuery.data.items));
  }, [attendanceQuery.data, classDate]);

  const saveMutation = useMutation({
    mutationFn: () =>
      saveAttendance(sectionId, {
        classDate: classDate ?? attendanceQuery.data!.classDate,
        items: attendanceQuery.data!.items.map((entry) => ({
          studentId: entry.studentId,
          status: statuses[entry.studentId]!,
        })),
      }),
    onSuccess: async (sheet) => {
        setStatuses(statusMap(sheet.items));
      await queryClient.invalidateQueries({ queryKey: ["attendance", sectionId] });
      message.success("Đã lưu điểm danh.");
    },
    onError: () => message.error("Không thể lưu điểm danh. Vui lòng kiểm tra dữ liệu và thử lại."),
  });

  const downloadMutation = useMutation({
    mutationFn: () => downloadAcademicReport(sectionId, "attendance"),
    onError: () => message.error("Không thể xuất danh sách điểm danh."),
  });

  const columns: ColumnsType<AttendanceEntry> = [
    { title: "MSSV", dataIndex: "studentCode", key: "studentCode", width: 140 },
    { title: "Họ và tên", dataIndex: "fullName", key: "fullName" },
    {
      title: "Trạng thái",
      key: "status",
      width: 180,
      render: (_, entry) => (
        <Select
          aria-label={`Điểm danh ${entry.fullName}`}
          placeholder="Chọn trạng thái"
          value={statuses[entry.studentId]}
          options={attendanceOptions}
          onChange={(status: AttendanceStatus) =>
            setStatuses((current) => ({ ...current, [entry.studentId]: status }))
          }
          style={{ width: "100%" }}
        />
      ),
    },
  ];

  const complete = Boolean(
    attendanceQuery.data?.items.every((entry) => statuses[entry.studentId] !== undefined),
  );

  return (
    <div className="academic-records-page">
      <Space wrap>
        <Select
          aria-label="Ngày điểm danh"
          placeholder="Chọn ngày học"
          loading={attendanceQuery.isLoading}
          value={classDate ?? attendanceQuery.data?.classDate}
          options={(attendanceQuery.data?.scheduledDates ?? []).map((date) => ({
            value: date,
            label: date,
          }))}
          onChange={setClassDate}
          style={{ minWidth: 180 }}
        />
        <Button
          icon={<DownloadOutlined />}
          loading={downloadMutation.isPending}
          onClick={() => downloadMutation.mutate()}
        >
          Xuất Excel điểm danh
        </Button>
        <Button
          type="primary"
          icon={<SaveOutlined />}
          loading={saveMutation.isPending}
          disabled={!attendanceQuery.data?.items.length || !complete}
          onClick={() => saveMutation.mutate()}
        >
          Lưu điểm danh
        </Button>
      </Space>

      {attendanceQuery.isLoading && <div className="feature-loading"><Spin /></div>}
      {attendanceQuery.isError && (
        <Alert
          type="error"
          showIcon
          message="Không tải được danh sách điểm danh."
          action={<Button size="small" onClick={() => void attendanceQuery.refetch()}>Thử lại</Button>}
        />
      )}
      {attendanceQuery.data && (
        <>
          <div className="academic-records-summary">
            <Tag color="processing">{attendanceQuery.data.sectionCode}</Tag>
            <span>Ngày học: {attendanceQuery.data.classDate}</span>
            <span>{attendanceQuery.data.items.length} sinh viên</span>
          </div>
          <Table<AttendanceEntry>
            rowKey="studentId"
            size="small"
            columns={columns}
            dataSource={attendanceQuery.data.items}
            pagination={{ pageSize: 15 }}
            locale={{ emptyText: "Lớp chưa có sinh viên đăng ký." }}
            scroll={{ x: 520 }}
          />
          {!complete && attendanceQuery.data.items.length > 0 && (
            <Alert type="info" showIcon message="Chọn trạng thái cho từng sinh viên trước khi lưu." />
          )}
        </>
      )}
    </div>
  );
}

export function SectionGradebookPage({ sectionId }: { sectionId: number }) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [scores, setScores] = useState<Record<number, Record<number, number | null>>>({});
  const gradeBookQuery = useQuery({
    queryKey: ["gradebook", sectionId],
    queryFn: () => fetchGradeBook(sectionId),
  });

  useEffect(() => {
    if (!gradeBookQuery.data) return;
    setScores(
      Object.fromEntries(
        gradeBookQuery.data.items.map((student) => [student.studentId, student.scores]),
      ),
    );
  }, [gradeBookQuery.data]);

  const saveMutation = useMutation({
    mutationFn: () =>
      saveGradeBook(sectionId, {
        items: gradeBookQuery.data!.items.map((student) => ({
          studentId: student.studentId,
          scores: scores[student.studentId] ?? student.scores,
        })),
      }),
    onSuccess: async (gradeBook) => {
      setScores(
        Object.fromEntries(gradeBook.items.map((student) => [student.studentId, student.scores])),
      );
      await queryClient.invalidateQueries({ queryKey: ["gradebook", sectionId] });
      message.success("Đã lưu bảng điểm.");
    },
    onError: () => message.error("Không thể lưu bảng điểm. Vui lòng kiểm tra dữ liệu và thử lại."),
  });

  const downloadMutation = useMutation({
    mutationFn: () => downloadAcademicReport(sectionId, "grades"),
    onError: () => message.error("Không thể xuất bảng điểm."),
  });

  const columns = useMemo<ColumnsType<StudentGradeRow>>(() => {
    const components: GradeComponent[] = gradeBookQuery.data?.components ?? [];
    return [
      { title: "MSSV", dataIndex: "studentCode", key: "studentCode", fixed: "left", width: 120 },
      { title: "Họ và tên", dataIndex: "fullName", key: "fullName", fixed: "left", width: 200 },
      ...components.map((component) => ({
        title: `${component.name} (${component.weightPercentage}%)`,
        key: `grade-${component.id}`,
        width: 150,
        render: (_: unknown, student: StudentGradeRow) => (
          <InputNumber
            aria-label={`${component.name} - ${student.fullName}`}
            min={0}
            max={component.maxScore}
            precision={2}
            value={scores[student.studentId]?.[component.id] ?? null}
            onChange={(value) =>
              setScores((current) => ({
                ...current,
                [student.studentId]: {
                  ...current[student.studentId],
                  [component.id]: value,
                },
              }))
            }
            style={{ width: "100%" }}
          />
        ),
      })),
      {
        title: "Điểm tổng kết",
        key: "finalScore",
        fixed: "right",
        width: 130,
        render: (_, student) =>
          student.finalScore === null ? "Chưa đủ điểm" : <strong>{student.finalScore}</strong>,
      },
    ];
  }, [gradeBookQuery.data?.components, scores]);

  return (
    <div className="academic-records-page">
      <Space wrap>
        <Button
          icon={<DownloadOutlined />}
          loading={downloadMutation.isPending}
          onClick={() => downloadMutation.mutate()}
        >
          Xuất Excel bảng điểm
        </Button>
        <Button
          type="primary"
          icon={<SaveOutlined />}
          loading={saveMutation.isPending}
          disabled={!gradeBookQuery.data?.components.length}
          onClick={() => saveMutation.mutate()}
        >
          Lưu bảng điểm
        </Button>
        <span>Điểm tổng kết được làm tròn về 0,5 gần nhất.</span>
      </Space>

      {gradeBookQuery.isLoading && <div className="feature-loading"><Spin /></div>}
      {gradeBookQuery.isError && (
        <Alert
          type="error"
          showIcon
          message="Không tải được bảng điểm."
          action={<Button size="small" onClick={() => void gradeBookQuery.refetch()}>Thử lại</Button>}
        />
      )}
      {gradeBookQuery.data && (
        <>
          <div className="academic-records-summary">
            <Tag color="processing">{gradeBookQuery.data.sectionCode}</Tag>
            {gradeBookQuery.data.components.map((component) => (
              <Tag key={component.id}>
                {component.name}: {component.weightPercentage}% · tối đa {component.maxScore}
              </Tag>
            ))}
          </div>
          {!gradeBookQuery.data.components.length && (
            <Alert
              type="warning"
              showIcon
              message="Lớp chưa được cấu hình các cột điểm."
              description="Liên hệ quản trị đào tạo để thiết lập trọng số trước khi nhập điểm."
            />
          )}
          <Table<StudentGradeRow>
            rowKey="studentId"
            size="small"
            columns={columns}
            dataSource={gradeBookQuery.data.items}
            pagination={{ pageSize: 15 }}
            locale={{ emptyText: "Lớp chưa có sinh viên đăng ký." }}
            scroll={{ x: true }}
          />
        </>
      )}
    </div>
  );
}
