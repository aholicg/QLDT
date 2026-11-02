import { useEffect, useState } from "react";
import { PlusOutlined } from "@ant-design/icons";
import { Alert, App, Button, Card, Empty, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Spin, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Section, SectionCreateRequest, SectionUpdateRequest, Subject, SubjectCreateRequest, SubjectUpdateRequest } from "../../shared/api/api-types";
import { readApiError } from "../../shared/api/client";
import GradeComponentsConfigModal from "./GradeComponentsConfigModal";
import { createSection, createSubject, deleteSection, deleteSubject, fetchCurrentSemester, fetchLookups, fetchSections, fetchSubjects, updateSection, updateSubject } from "./catalogApi";

const PAGE_SIZE = 10;
const DAYS = [2, 3, 4, 5, 6, 7, 8].map((value) => ({ value, label: value === 8 ? "Chủ nhật" : `Thứ ${value}` }));

function errorText(error: unknown) {
  const body = readApiError(error);
  const details = body?.details?.map((item) => item.message).filter(Boolean).join("; ");
  return details || body?.message || "Thao tác chưa thành công. Vui lòng thử lại.";
}

export default function AdminCatalogPage({ resource }: { resource: "subjects" | "sections" }) {
  const isSubjects = resource === "subjects";
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState("");
  const [subjectModalOpen, setSubjectModalOpen] = useState(false);
  const [sectionModalOpen, setSectionModalOpen] = useState(false);
  const [subjectEditor, setSubjectEditor] = useState<Subject>();
  const [sectionEditor, setSectionEditor] = useState<Section>();
  const [gradeConfigSection, setGradeConfigSection] = useState<Section>();

  const lookupsQuery = useQuery({ queryKey: ["catalog", "lookups"], queryFn: fetchLookups, enabled: !isSubjects });
  const currentSemesterQuery = useQuery({ queryKey: ["semesters", "current"], queryFn: fetchCurrentSemester, enabled: !isSubjects });
  const [selectedSemesterId, setSelectedSemesterId] = useState<number>();
  const semesterId = selectedSemesterId ?? currentSemesterQuery.data?.id;
  useEffect(() => {
    if (selectedSemesterId === undefined && currentSemesterQuery.data) {
      setSelectedSemesterId(currentSemesterQuery.data.id);
    }
  }, [currentSemesterQuery.data, selectedSemesterId]);
  const subjectsQuery = useQuery({
    queryKey: ["subjects", page, keyword],
    enabled: isSubjects,
    queryFn: () => fetchSubjects({ page, size: PAGE_SIZE, keyword: keyword || undefined }),
  });
  const sectionsQuery = useQuery({
    queryKey: ["sections", "admin", semesterId, page, keyword],
    enabled: !isSubjects && semesterId !== undefined,
    queryFn: () => fetchSections({ semesterId: semesterId!, page, size: PAGE_SIZE, keyword: keyword || undefined }),
  });
  const query = isSubjects ? subjectsQuery : sectionsQuery;
  const onSuccess = async (label: string) => {
    await queryClient.invalidateQueries({ queryKey: [isSubjects ? "subjects" : "sections"] });
    setSubjectModalOpen(false);
    setSectionModalOpen(false);
    message.success(label);
  };
  const subjectCreateMutation = useMutation({ mutationFn: createSubject, onSuccess: () => onSuccess("Đã tạo môn học."), onError: (error: unknown) => message.error(errorText(error)) });
  const subjectUpdateMutation = useMutation({ mutationFn: ({ id, body }: { id: number; body: SubjectUpdateRequest }) => updateSubject(id, body), onSuccess: () => onSuccess("Đã cập nhật môn học."), onError: (error: unknown) => message.error(errorText(error)) });
  const subjectDeleteMutation = useMutation({ mutationFn: deleteSubject, onSuccess: () => onSuccess("Đã xóa môn học."), onError: (error: unknown) => message.error(errorText(error)) });
  const sectionCreateMutation = useMutation({ mutationFn: createSection, onSuccess: () => onSuccess("Đã tạo lớp học phần."), onError: (error: unknown) => message.error(errorText(error)) });
  const sectionUpdateMutation = useMutation({ mutationFn: ({ id, body }: { id: number; body: SectionUpdateRequest }) => updateSection(id, body), onSuccess: () => onSuccess("Đã cập nhật lớp học phần."), onError: (error: unknown) => message.error(errorText(error)) });
  const sectionDeleteMutation = useMutation({ mutationFn: deleteSection, onSuccess: () => onSuccess("Đã xóa lớp học phần."), onError: (error: unknown) => message.error(errorText(error)) });
  const busy = subjectCreateMutation.isPending || subjectUpdateMutation.isPending || sectionCreateMutation.isPending || sectionUpdateMutation.isPending;

  const subjectColumns: ColumnsType<Subject> = [
    { title: "Mã môn", dataIndex: "subjectCode", key: "subjectCode", width: 130, render: (value: string) => <Typography.Text strong>{value}</Typography.Text> },
    { title: "Tên môn học", dataIndex: "name", key: "name" },
    { title: "Tín chỉ", dataIndex: "credits", key: "credits", width: 90, align: "center" },
    { title: "Lớp đã mở", dataIndex: "sectionCount", key: "sectionCount", width: 110, align: "center" },
    { title: "Thao tác", key: "actions", width: 150, render: (_, row) => <Space><Button size="small" onClick={() => { setSubjectEditor(row); setSubjectModalOpen(true); }}>Sửa</Button><Popconfirm title="Xóa môn học này?" description={row.sectionCount ? "Môn đang có lớp học phần và không thể xóa." : undefined} okText="Xóa" cancelText="Hủy" onConfirm={() => subjectDeleteMutation.mutateAsync(row.id)}><Button danger size="small" disabled={row.sectionCount > 0}>Xóa</Button></Popconfirm></Space> },
  ];
  const sectionColumns: ColumnsType<Section> = [
    { title: "Mã lớp", dataIndex: "sectionCode", key: "sectionCode", width: 120, render: (value: string) => <Typography.Text strong>{value}</Typography.Text> },
    { title: "Môn học", key: "subject", render: (_, row) => <Space direction="vertical" size={0}><span>{row.subject.name}</span><Typography.Text type="secondary">{row.subject.subjectCode}</Typography.Text></Space> },
    { title: "Giảng viên", key: "lecturer", render: (_, row) => row.lecturer.fullName },
    { title: "Phòng", key: "room", render: (_, row) => <Tag color="blue">{row.room.roomCode}</Tag> },
    { title: "Lịch", key: "schedule", render: (_, row) => `Thứ ${row.dayOfWeek} · Tiết ${row.startPeriod}-${row.endPeriod} · Tuần ${row.startWeek}-${row.endWeek}` },
    { title: "Sĩ số", key: "capacity", width: 90, render: (_, row) => `${row.currentEnrollment}/${row.maxCapacity}` },
    { title: "Thao tác", key: "actions", width: 250, render: (_, row) => <Space wrap><Button size="small" onClick={() => { setSectionEditor(row); setSectionModalOpen(true); }}>Sửa</Button><Button size="small" onClick={() => setGradeConfigSection(row)}>Cấu hình điểm</Button><Popconfirm title="Xóa lớp học phần?" description={row.currentEnrollment ? "Lớp đã có đăng ký nên backend có thể từ chối thao tác này." : undefined} okText="Xóa" cancelText="Hủy" onConfirm={() => sectionDeleteMutation.mutateAsync(row.id)}><Button danger size="small">Xóa</Button></Popconfirm></Space> },
  ];

  const sectionInitialValues: Partial<SectionCreateRequest> = sectionEditor ? {
    sectionCode: sectionEditor.sectionCode,
    subjectId: sectionEditor.subject.id,
    semesterId: sectionEditor.semester.id,
    lecturerId: sectionEditor.lecturer.id,
    roomId: sectionEditor.room.id,
    dayOfWeek: sectionEditor.dayOfWeek,
    startPeriod: sectionEditor.startPeriod,
    endPeriod: sectionEditor.endPeriod,
    startWeek: sectionEditor.startWeek,
    endWeek: sectionEditor.endWeek,
    maxCapacity: sectionEditor.maxCapacity,
  } : { semesterId };

  return (
    <div className="admin-catalog-page">
      <style>{`
        .admin-catalog-page { display: grid; gap: 16px; }
        .admin-catalog-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
        .admin-catalog-toolbar .ant-input-affix-wrapper { max-width: 420px; }
        .admin-catalog-table { overflow: hidden; }
        @media (max-width: 640px) { .admin-catalog-toolbar { align-items: stretch; flex-direction: column; } .admin-catalog-toolbar .ant-input-affix-wrapper { max-width: none; width: 100%; } }
      `}</style>
      {!isSubjects && currentSemesterQuery.data && <Tag color="processing">Học kỳ hiện tại: {currentSemesterQuery.data.semesterCode} · {currentSemesterQuery.data.name}</Tag>}
      {(query.isError || (!isSubjects && lookupsQuery.isError)) && <Alert type="error" showIcon message="Không tải được danh mục." action={<Button size="small" onClick={() => void query.refetch()}>Thử lại</Button>} />}
      <Card className="admin-catalog-table" styles={{ body: { padding: 0 } }}>
        <div className="admin-catalog-toolbar" style={{ padding: 16 }}>
          {!isSubjects && <Select aria-label="Học kỳ" value={semesterId} options={(lookupsQuery.data?.semesters ?? []).map((semester) => ({ value: semester.id, label: `${semester.semesterCode} · ${semester.name}` }))} onChange={(value) => { setSelectedSemesterId(value); setPage(1); }} style={{ minWidth: 220 }} />}
          <Input.Search allowClear value={keyword} placeholder={isSubjects ? "Tìm mã hoặc tên môn học" : "Tìm mã lớp hoặc môn học"} onChange={(event) => { setKeyword(event.target.value); setPage(1); }} aria-label="Tìm trong danh mục" />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { if (isSubjects) { setSubjectEditor(undefined); setSubjectModalOpen(true); } else { setSectionEditor(undefined); setSectionModalOpen(true); } }}>{isSubjects ? "Thêm môn học" : "Mở lớp học phần"}</Button>
        </div>
        {query.isLoading && <div style={{ padding: 36, textAlign: "center" }}><Spin /></div>}
        {isSubjects && subjectsQuery.data && <Table<Subject> rowKey="id" columns={subjectColumns} dataSource={subjectsQuery.data.items} scroll={{ x: 720 }} pagination={{ current: page, pageSize: PAGE_SIZE, total: subjectsQuery.data.totalItems, showSizeChanger: false }} onChange={(pagination) => setPage(pagination.current ?? 1)} locale={{ emptyText: <Empty description="Chưa có môn học phù hợp." /> }} />}
        {query.isSuccess && !isSubjects && <Table<Section> rowKey="id" columns={sectionColumns} dataSource={sectionsQuery.data?.items ?? []} scroll={{ x: 1050 }} pagination={{ current: page, pageSize: PAGE_SIZE, total: sectionsQuery.data?.totalItems ?? 0, showSizeChanger: false }} onChange={(pagination) => setPage(pagination.current ?? 1)} locale={{ emptyText: <Empty description="Học kỳ chưa có lớp học phần phù hợp." /> }} />}
      </Card>

      <Modal title={subjectEditor ? `Sửa môn ${subjectEditor.subjectCode}` : "Thêm môn học"} open={subjectModalOpen} onCancel={() => setSubjectModalOpen(false)} footer={null} destroyOnHidden>
        <Form<SubjectCreateRequest> key={subjectEditor?.id ?? "new-subject"} layout="vertical" initialValues={subjectEditor} onFinish={(values) => subjectEditor ? subjectUpdateMutation.mutate({ id: subjectEditor.id, body: { name: values.name, credits: values.credits, description: values.description } }) : subjectCreateMutation.mutate(values)}>
          {!subjectEditor && <Form.Item label="Mã môn học" name="subjectCode" rules={[{ required: true, whitespace: true, message: "Nhập mã môn học" }, { max: 20 }]}><Input maxLength={20} /></Form.Item>}
          <Form.Item label="Tên môn học" name="name" rules={[{ required: true, whitespace: true, message: "Nhập tên môn học" }, { max: 150 }]}><Input maxLength={150} /></Form.Item>
          <Form.Item label="Số tín chỉ" name="credits" rules={[{ required: true, message: "Nhập số tín chỉ" }]}><InputNumber min={1} style={{ width: "100%" }} /></Form.Item>
          <Form.Item label="Mô tả" name="description"><Input.TextArea rows={3} /></Form.Item>
          <Button type="primary" htmlType="submit" loading={busy} block>{subjectEditor ? "Lưu thay đổi" : "Tạo môn học"}</Button>
        </Form>
      </Modal>

      <Modal title={sectionEditor ? `Sửa lớp ${sectionEditor.sectionCode}` : "Mở lớp học phần"} open={sectionModalOpen} onCancel={() => setSectionModalOpen(false)} footer={null} width={720} destroyOnHidden>
        <Form<SectionCreateRequest> key={sectionEditor?.id ?? `new-section-${semesterId ?? ""}`} layout="vertical" initialValues={sectionInitialValues} onFinish={(values) => {
          if (sectionEditor) {
            const { sectionCode: _sectionCode, ...body } = values;
            sectionUpdateMutation.mutate({ id: sectionEditor.id, body: body as SectionUpdateRequest });
          } else sectionCreateMutation.mutate(values);
        }}>
          {!sectionEditor && <Form.Item label="Mã lớp học phần" name="sectionCode" rules={[{ required: true, whitespace: true, message: "Nhập mã lớp" }, { max: 20 }]}><Input maxLength={20} /></Form.Item>}
          <Space style={{ display: "flex" }} size={12}>
            <Form.Item label="Môn học" name="subjectId" rules={[{ required: true }]} style={{ flex: 1 }}><Select showSearch optionFilterProp="label" options={(lookupsQuery.data?.subjects ?? []).map((item) => ({ value: item.id, label: `${item.subjectCode} · ${item.name}` }))} /></Form.Item>
            <Form.Item label="Học kỳ" name="semesterId" rules={[{ required: true }]} style={{ flex: 1 }}><Select options={(lookupsQuery.data?.semesters ?? []).map((item) => ({ value: item.id, label: `${item.semesterCode} · ${item.name}` }))} /></Form.Item>
          </Space>
          <Space style={{ display: "flex" }} size={12}>
            <Form.Item label="Giảng viên" name="lecturerId" rules={[{ required: true }]} style={{ flex: 1 }}><Select showSearch optionFilterProp="label" options={(lookupsQuery.data?.lecturers ?? []).map((item) => ({ value: item.id, label: `${item.lecturerCode} · ${item.fullName}` }))} /></Form.Item>
            <Form.Item label="Phòng học" name="roomId" rules={[{ required: true }]} style={{ flex: 1 }}><Select showSearch optionFilterProp="label" options={(lookupsQuery.data?.rooms ?? []).map((item) => ({ value: item.id, label: `${item.roomCode} · ${item.capacity} chỗ` }))} /></Form.Item>
          </Space>
          <Space style={{ display: "flex" }} size={12}>
            <Form.Item label="Thứ" name="dayOfWeek" rules={[{ required: true }]} style={{ flex: 1 }}><Select options={DAYS} /></Form.Item>
            <Form.Item label="Tiết bắt đầu" name="startPeriod" rules={[{ required: true }]} style={{ flex: 1 }}><InputNumber min={1} max={12} style={{ width: "100%" }} /></Form.Item>
            <Form.Item label="Tiết kết thúc" name="endPeriod" rules={[{ required: true }]} style={{ flex: 1 }}><InputNumber min={1} max={12} style={{ width: "100%" }} /></Form.Item>
          </Space>
          <Space style={{ display: "flex" }} size={12}>
            <Form.Item label="Tuần bắt đầu" name="startWeek" rules={[{ required: true }]} style={{ flex: 1 }}><InputNumber min={1} style={{ width: "100%" }} /></Form.Item>
            <Form.Item label="Tuần kết thúc" name="endWeek" rules={[{ required: true }]} style={{ flex: 1 }}><InputNumber min={1} style={{ width: "100%" }} /></Form.Item>
            <Form.Item label="Sĩ số tối đa" name="maxCapacity" rules={[{ required: true }]} style={{ flex: 1 }}><InputNumber min={1} style={{ width: "100%" }} /></Form.Item>
          </Space>
          <Alert type="info" showIcon message="Kiểm tra dữ liệu và xung đột được thực hiện phía máy chủ trước khi lưu." style={{ marginBottom: 16 }} />
          <Button type="primary" htmlType="submit" loading={busy} block>{sectionEditor ? "Lưu thay đổi" : "Tạo lớp học phần"}</Button>
        </Form>
      </Modal>
      {gradeConfigSection && (
        <GradeComponentsConfigModal
          section={gradeConfigSection}
          onClose={() => setGradeConfigSection(undefined)}
        />
      )}
    </div>
  );
}
