import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Alert, Button, Card, Empty, Progress, Select, Spin, Tag, message } from "antd";
import api, { readApiError, requireItems } from "../../shared/api/client";
import type { Registration, Semester } from "../../shared/api/api-types";

interface ItemsResponse<T> { items: T[]; }

const MIN_CREDITS = 12;
const MAX_CREDITS = 24;
const days: Record<number, string> = { 2: "Thứ hai", 3: "Thứ ba", 4: "Thứ tư", 5: "Thứ năm", 6: "Thứ sáu", 7: "Thứ bảy", 8: "Chủ nhật" };

function serverDetails(error: unknown) {
  const body = readApiError(error);
  return body?.details.map((detail) => detail.message).filter(Boolean) ?? [];
}

export default function MyRegistrationsPage() {
  const { modal } = App.useApp();
  const queryClient = useQueryClient();
  const [semesterId, setSemesterId] = useState<number>();
  const [messageApi, contextHolder] = message.useMessage();

  const semestersQuery = useQuery({
    queryKey: ["semesters"],
    queryFn: async () => requireItems<Semester>((await api.get<ItemsResponse<Semester>>("/semesters")).data),
  });

  useEffect(() => {
    if (semesterId === undefined && semestersQuery.data?.length) setSemesterId(semestersQuery.data[0].id);
  }, [semestersQuery.data, semesterId]);

  const registrationsQuery = useQuery({
    queryKey: ["registrations", semesterId],
    enabled: semesterId !== undefined,
    queryFn: async () => requireItems<Registration>((await api.get<ItemsResponse<Registration>>("/registrations/me", { params: { semesterId } })).data),
  });
  const registrations = registrationsQuery.data ?? [];
  const totalCredits = useMemo(() => registrations.reduce((total, registration) => total + registration.section.subject.credits, 0), [registrations]);
  const progressPercent = Math.min(100, Math.round((totalCredits / MAX_CREDITS) * 100));

  const cancelMutation = useMutation({
    mutationFn: (registrationId: number) => api.delete(`/registrations/${registrationId}`),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["registrations", semesterId] }),
        queryClient.invalidateQueries({ queryKey: ["sections", semesterId] }),
        queryClient.invalidateQueries({ queryKey: ["timetable"] }),
      ]);
      messageApi.success("Đã hủy đăng ký.");
    },
    onError: (error: unknown) => {
      const body = readApiError(error);
      const details = serverDetails(error);
      const messages: Record<string, string> = {
        FORBIDDEN: "Bạn không có quyền hủy đăng ký này.",
        NOT_FOUND: "Không tìm thấy bản ghi đăng ký. Danh sách có thể đã thay đổi.",
        CREDIT_LIMIT_BELOW_MIN: "Không thể hủy vì số tín chỉ sẽ thấp hơn mức tối thiểu của học kỳ.",
      };
      messageApi.error([messages[body?.error ?? ""] ?? "Không thể hủy đăng ký.", details.length ? details.join("; ") : body?.message].filter(Boolean).join(" "));
    },
  });

  function confirmCancellation(registration: Registration) {
    modal.confirm({
      title: "Hủy đăng ký học phần?",
      content: `${registration.section.subject.name} · ${registration.section.sectionCode}`,
      okText: "Hủy đăng ký",
      okButtonProps: { danger: true },
      cancelText: "Giữ đăng ký",
      onOk: () => cancelMutation.mutateAsync(registration.id),
    });
  }

  return (
    <>
      {contextHolder}
      <div className="feature-toolbar">
        <Select aria-label="Học kỳ" className="semester-select" placeholder="Chọn học kỳ" loading={semestersQuery.isLoading} value={semesterId}
          options={(semestersQuery.data ?? []).map((semester) => ({ value: semester.id, label: `${semester.semesterCode} · ${semester.name}` }))} onChange={setSemesterId} />
      </div>
      {semestersQuery.isError && <Alert type="error" showIcon message="Không tải được danh sách học kỳ." action={<Button size="small" onClick={() => void semestersQuery.refetch()}>Thử lại</Button>} />}
      {semesterId !== undefined && !registrationsQuery.isLoading && !registrationsQuery.isError && <Card className="registration-summary-card">
        <div><span className="eyebrow">TỔNG HỢP HỌC KỲ</span><strong>Tổng số tín chỉ đã đăng ký: {totalCredits} tín chỉ</strong><span>Tổng số lớp: {registrations.length} lớp</span></div>
        <div className="registration-credit-progress"><Progress percent={progressPercent} strokeColor={totalCredits > MAX_CREDITS ? "#c2410c" : "#38745e"} showInfo={false} /><span>{totalCredits < MIN_CREDITS ? `Còn thiếu ${MIN_CREDITS - totalCredits} tín chỉ tối thiểu` : totalCredits >= MAX_CREDITS ? "Đã đạt mức tối đa 24 tín chỉ" : `Còn ${MAX_CREDITS - totalCredits} tín chỉ có thể đăng ký`}</span></div>
        <Tag color={totalCredits < MIN_CREDITS ? "warning" : "success"}>{MIN_CREDITS}–{MAX_CREDITS} tín chỉ/kỳ</Tag>
      </Card>}
      {semesterId === undefined && !semestersQuery.isError && <div className="feature-empty"><Empty description="Chọn học kỳ để xem các lớp đã đăng ký." /></div>}
      {registrationsQuery.isLoading && <div className="feature-loading"><Spin /></div>}
      {registrationsQuery.isError && <Alert type="error" showIcon message="Không tải được đăng ký học phần." action={<Button size="small" onClick={() => void registrationsQuery.refetch()}>Thử lại</Button>} />}
      {registrationsQuery.data?.length === 0 && <div className="feature-empty"><Empty description="Chưa có lớp học phần trong học kỳ này." /></div>}
      <div className="registration-list">
        {registrations.map((registration) => {
          const section = registration.section;
          return <Card key={registration.id} className="registration-card"><div className="registration-card-main"><div><div className="section-card-top"><span className="section-code">{section.sectionCode}</span><Tag color="blue">{section.subject.credits} tín chỉ</Tag></div><h3>{section.subject.name}</h3><p className="section-subtitle">{section.subject.subjectCode}</p><div className="section-details"><span>{days[section.dayOfWeek] ?? `Thứ ${section.dayOfWeek}`} · Tiết {section.startPeriod}-{section.endPeriod}</span><span>Tuần {section.startWeek}-{section.endWeek}</span></div></div><Button danger loading={cancelMutation.isPending && cancelMutation.variables === registration.id} onClick={() => confirmCancellation(registration)}>Hủy đăng ký</Button></div></Card>;
        })}
      </div>
    </>
  );
}
