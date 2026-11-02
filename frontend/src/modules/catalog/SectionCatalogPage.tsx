import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Alert, Button, Card, Checkbox, Empty, Input, Select, Spin, Table, Tag, message } from "antd";
import { DeleteOutlined, PlusOutlined, SearchOutlined, ShoppingCartOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import api, { readApiError, requireItems } from "../../shared/api/client";
import { useAuth } from "../auth/AuthContext";
import type { Registration, Section, Semester } from "../../shared/api/api-types";
import { fetchSections } from "./catalogApi";

interface ItemsResponse<T> { items: T[]; }
type Shift = "MORNING" | "AFTERNOON" | undefined;

const pageSize = 10;
const MIN_CREDITS = 12;
const MAX_CREDITS = 24;
const days: Record<number, string> = { 2: "Thứ 2", 3: "Thứ 3", 4: "Thứ 4", 5: "Thứ 5", 6: "Thứ 6", 7: "Thứ 7" };
const dayColumns = [2, 3, 4, 5, 6, 7];

function scheduleLabel(section: Section) {
  return `${days[section.dayOfWeek] ?? `Thứ ${section.dayOfWeek}`} · Tiết ${section.startPeriod}-${section.endPeriod} · Tuần ${section.startWeek}-${section.endWeek}`;
}

function overlaps(a: Section, b: Section) {
  return a.dayOfWeek === b.dayOfWeek && a.startPeriod <= b.endPeriod && b.startPeriod <= a.endPeriod && a.startWeek <= b.endWeek && b.startWeek <= a.endWeek;
}

function sectionIsConflicting(section: Section, sections: Section[]) {
  return sections.some((other) => other.id !== section.id && overlaps(section, other));
}

function errorDescription(error: unknown) {
  const body = readApiError(error);
  const details = body?.details.map((detail) => detail.message).filter(Boolean) ?? [];
  return details.length ? details.join("; ") : body?.message;
}

export default function SectionCatalogPage() {
  const { modal } = App.useApp();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [semesterId, setSemesterId] = useState<number>();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [unitKeyword, setUnitKeyword] = useState("");
  const [selectedDays, setSelectedDays] = useState<number[]>([]);
  const [shift, setShift] = useState<Shift>();
  const [hideConflicts, setHideConflicts] = useState(false);
  const [onlyAvailable, setOnlyAvailable] = useState(false);
  const [cart, setCart] = useState<Section[]>([]);
  const [cartHydrated, setCartHydrated] = useState(false);
  const [batchSubmitting, setBatchSubmitting] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();
  const storageKey = user ? `qldt_cart_sections_${user.studentCode ?? user.userId}` : undefined;

  const semestersQuery = useQuery({ queryKey: ["semesters"], queryFn: async () => requireItems<Semester>((await api.get<ItemsResponse<Semester>>("/semesters")).data) });
  useEffect(() => { if (semesterId === undefined && semestersQuery.data?.length) setSemesterId(semestersQuery.data[0].id); }, [semestersQuery.data, semesterId]);
  useEffect(() => {
    if (!storageKey || semesterId === undefined) return;
    setCartHydrated(false);
    try {
      const stored = JSON.parse(localStorage.getItem(storageKey) ?? "[]") as Section[];
      setCart(stored.filter((section) => section.semester.id === semesterId));
    } catch { setCart([]); } finally { setCartHydrated(true); }
  }, [storageKey, semesterId]);
  useEffect(() => {
    if (!storageKey || !cartHydrated) return;
    if (cart.length) localStorage.setItem(storageKey, JSON.stringify(cart));
    else localStorage.removeItem(storageKey);
  }, [cart, cartHydrated, storageKey]);

  const sectionsQuery = useQuery({
    queryKey: ["sections", semesterId, page, search, unitKeyword],
    enabled: semesterId !== undefined,
    queryFn: () => fetchSections({ semesterId: semesterId!, page, size: pageSize, keyword: search.trim() || undefined, unitKeyword: unitKeyword.trim() || undefined }),
  });
  const registrationsQuery = useQuery({
    queryKey: ["registrations", semesterId], enabled: semesterId !== undefined,
    queryFn: async () => requireItems<Registration>((await api.get<ItemsResponse<Registration>>("/registrations/me", { params: { semesterId } })).data),
  });
  const registeredSections = useMemo(() => (registrationsQuery.data ?? []).map((registration) => registration.section), [registrationsQuery.data]);
  const sections = sectionsQuery.data?.items ?? [];
  const visibleSections = useMemo(() => sections.filter((section) => {
    const dayMatches = !selectedDays.length || selectedDays.includes(section.dayOfWeek);
    const shiftMatches = !shift || (shift === "MORNING" ? section.startPeriod <= 6 : section.endPeriod >= 7);
    return dayMatches && shiftMatches && (!onlyAvailable || !section.full) && (!hideConflicts || !sectionIsConflicting(section, registeredSections));
  }), [hideConflicts, onlyAvailable, registeredSections, sections, selectedDays, shift]);
  const cartCredits = cart.reduce((total, section) => total + section.subject.credits, 0);
  const cartHasConflict = cart.some((section) => sectionIsConflicting(section, [...registeredSections, ...cart]));
  const cartCreditsInvalid = cartCredits > MAX_CREDITS;
  const timetableItems = useMemo(() => {
    const items = [...registeredSections.map((section) => ({ section, source: "registered" as const, conflict: false })), ...cart.map((section) => ({ section, source: "cart" as const, conflict: sectionIsConflicting(section, [...registeredSections, ...cart]) }))];
    return items.filter((item, index, all) => all.findIndex((other) => other.section.id === item.section.id) === index);
  }, [cart, registeredSections]);

  async function invalidateRegistrationQueries() {
    await Promise.all([queryClient.invalidateQueries({ queryKey: ["sections", semesterId] }), queryClient.invalidateQueries({ queryKey: ["registrations", semesterId] }), queryClient.invalidateQueries({ queryKey: ["timetable"] })]);
  }
  const registrationMutation = useMutation({
    mutationFn: (sectionId: number) => api.post("/registrations", { sectionId }),
    onSuccess: async (_response, sectionId) => { setCart((current) => current.filter((section) => section.id !== sectionId)); await invalidateRegistrationQueries(); messageApi.success("Đăng ký thành công. Dữ liệu đã được đồng bộ."); },
    onError: (error: unknown) => { const body = readApiError(error); const names: Record<string, string> = { CLASS_FULL: "Lớp học phần đã đủ sĩ số.", ALREADY_REGISTERED: "Bạn đã đăng ký lớp học phần này.", SAME_SUBJECT_REGISTERED: "Bạn đã đăng ký một lớp khác của môn học này.", STUDENT_SCHEDULE_CONFLICT: "Lịch học bị trùng với lớp đã đăng ký.", CREDIT_LIMIT_EXCEEDED: "Đăng ký vượt quá số tín chỉ tối đa trong học kỳ." }; messageApi.error([names[body?.error ?? ""] ?? "Không thể đăng ký lúc này.", errorDescription(error)].filter(Boolean).join(" ")); void invalidateRegistrationQueries(); },
  });

  function addToCart(section: Section) {
    if (cart.some((item) => item.id === section.id)) return;
    if (cart.some((item) => item.subject.id === section.subject.id)) { messageApi.warning("Mỗi môn chỉ được chọn một lớp trong giỏ."); return; }
    setCart((current) => [...current, section]); messageApi.success(`${section.sectionCode} đã được thêm vào giỏ.`);
  }
  function confirmRegistration(section: Section) { modal.confirm({ title: "Xác nhận đăng ký lớp học phần", content: `${section.subject.subjectCode} · ${section.sectionCode} · ${section.subject.credits} tín chỉ`, okText: "Đăng ký", cancelText: "Để sau", onOk: () => registrationMutation.mutateAsync(section.id) }); }
  async function submitCart() {
    if (!cart.length || cartHasConflict || cartCreditsInvalid) return;
    setBatchSubmitting(true);
    const results = await Promise.allSettled(cart.map((section) => api.post("/registrations", { sectionId: section.id })));
    const successIds = cart.filter((_section, index) => results[index].status === "fulfilled").map((section) => section.id);
    const failures = results.map((result, index) => result.status === "rejected" ? `${cart[index].sectionCode}: ${errorDescription(result.reason) ?? "Không rõ nguyên nhân"}` : undefined).filter(Boolean) as string[];
    setCart((current) => current.filter((section) => !successIds.includes(section.id)));
    if (storageKey && successIds.length === cart.length) localStorage.removeItem(storageKey);
    await invalidateRegistrationQueries(); setBatchSubmitting(false);
    if (successIds.length) messageApi.success(`Đã gửi thành công ${successIds.length}/${cart.length} lớp đăng ký.`);
    if (failures.length) messageApi.error(`${failures.length} lớp đăng ký thất bại: ${failures.join("; ")}`, 8);
  }
  function resetFilters() { setSearch(""); setUnitKeyword(""); setSelectedDays([]); setShift(undefined); setHideConflicts(false); setOnlyAvailable(false); setPage(1); }

  const sectionColumns: ColumnsType<Section> = [
    { title: "Mã lớp", dataIndex: "sectionCode", key: "sectionCode", width: 120, render: (value: string) => <strong className="section-code">{value}</strong> },
    { title: "Mã học phần", dataIndex: ["subject", "subjectCode"], key: "subjectCode", width: 125 },
    { title: "Tên học phần", dataIndex: ["subject", "name"], key: "subjectName", width: 220, ellipsis: true },
    { title: "TC", dataIndex: ["subject", "credits"], key: "credits", width: 55, align: "center" },
    { title: "Lịch học", key: "schedule", width: 175, render: (_, section) => `${days[section.dayOfWeek] ?? `Thứ ${section.dayOfWeek}`} · Tiết ${section.startPeriod}-${section.endPeriod}` },
    { title: "Tuần học", key: "weeks", width: 95, render: (_, section) => `${section.startWeek}-${section.endWeek}` },
    { title: "Phòng", key: "room", width: 90, render: (_, section) => section.room.roomCode },
    { title: "Giảng viên", key: "lecturer", width: 160, ellipsis: true, render: (_, section) => section.lecturer.fullName },
    { title: "Trạng thái chỗ", key: "capacity", width: 135, render: (_, section) => section.registeredByMe ? <Tag color="blue">Đã đăng ký</Tag> : <Tag color={section.full ? "error" : "success"}>{section.full ? "Đã đầy" : `${section.remainingSeats} / ${section.maxCapacity}`}</Tag> },
    { title: "Hành động", key: "action", fixed: "right", width: 145, render: (_, section) => { const inCart = cart.some((item) => item.id === section.id); const sameSubject = cart.some((item) => item.subject.id === section.subject.id); if (section.registeredByMe) return <Tag color="blue">Đã đăng ký</Tag>; return <Button size="small" type={inCart ? "default" : "primary"} icon={inCart ? undefined : <PlusOutlined />} disabled={section.full || inCart || sameSubject} onClick={() => addToCart(section)}>{inCart ? "Đã trong giỏ" : sameSubject ? "Đã chọn môn" : "Thêm vào giỏ"}</Button>; } },
  ];

  return <>
    {contextHolder}
    <div className="feature-toolbar registration-toolbar registration-filter-toolbar">
      <Select aria-label="Học kỳ" className="semester-select" placeholder="Chọn học kỳ" loading={semestersQuery.isLoading} value={semesterId} options={(semestersQuery.data ?? []).map((semester) => ({ value: semester.id, label: `${semester.semesterCode} · ${semester.name}` }))} onChange={(value: number) => { setSemesterId(value); setPage(1); setCart([]); setCartHydrated(false); }} />
      <Input allowClear aria-label="Tìm mã lớp hoặc học phần" className="section-search" placeholder="Mã lớp / mã học phần / tên học phần" prefix={<SearchOutlined />} value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} />
      <Input allowClear aria-label="Tìm Trường Viện Khoa" className="unit-search" placeholder="Trường / Viện / Khoa" value={unitKeyword} onChange={(event) => { setUnitKeyword(event.target.value); setPage(1); }} />
      <Select aria-label="Thứ trong tuần" mode="multiple" className="day-filter" placeholder="Thứ trong tuần" value={selectedDays} options={dayColumns.map((day) => ({ value: day, label: days[day] }))} onChange={setSelectedDays} />
      <Select aria-label="Kíp học" className="shift-filter" allowClear placeholder="Kíp sáng / chiều" value={shift} options={[{ value: "MORNING", label: "Kíp sáng · Tiết 1–6" }, { value: "AFTERNOON", label: "Kíp chiều · Tiết 7–12" }]} onChange={setShift} />
      <Button onClick={resetFilters}>Xóa bộ lọc</Button>
    </div>
    <div className="registration-filter-options"><Checkbox checked={hideConflicts} onChange={(event) => setHideConflicts(event.target.checked)}>Ẩn lớp trùng lịch hiện tại</Checkbox><Checkbox checked={onlyAvailable} onChange={(event) => setOnlyAvailable(event.target.checked)}>Chỉ hiện lớp còn chỗ</Checkbox></div>
    {semestersQuery.isError && <Alert type="error" showIcon message="Không tải được danh sách học kỳ." action={<Button size="small" onClick={() => void semestersQuery.refetch()}>Thử lại</Button>} />}
    {sectionsQuery.isLoading && <div className="feature-loading"><Spin /></div>}
    {sectionsQuery.isError && <Alert type="error" showIcon message="Không tải được lớp học phần." action={<Button size="small" onClick={() => void sectionsQuery.refetch()}>Thử lại</Button>} />}
    {semesterId !== undefined && !sectionsQuery.isLoading && !sectionsQuery.isError && <div className="registration-layout"><section>
      <div className="registration-section-heading"><div><span className="eyebrow">DANH SÁCH LỚP MỞ</span><h3>Chọn lớp học phần</h3></div><span className="result-count">{visibleSections.length}/{sections.length} lớp trên trang</span></div>
      {!visibleSections.length ? <div className="feature-empty"><Empty description="Không có lớp phù hợp với bộ lọc hiện tại." /></div> : <Table<Section> className="registration-section-table" rowKey="id" size="small" columns={sectionColumns} dataSource={visibleSections} pagination={false} scroll={{ x: 1290 }} locale={{ emptyText: "Không có lớp phù hợp." }} />}
      {(sectionsQuery.data?.totalItems ?? 0) > 0 && <div className="feature-pagination"><Button disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Trước</Button><span>Trang {page}/{sectionsQuery.data?.totalPages ?? 1} · Tổng {sectionsQuery.data?.totalItems ?? 0} lớp</span><Button disabled={page >= (sectionsQuery.data?.totalPages ?? 1)} onClick={() => setPage((value) => value + 1)}>Tiếp</Button></div>}
    </section>
    <aside className="registration-sidebar"><Card className="registration-cart" title={<span><ShoppingCartOutlined /> Giỏ môn học</span>} extra={<Tag color={cart.length ? "blue" : "default"}>{cart.length} lớp · {cartCredits} TC</Tag>}><div className="cart-summary"><strong>{cartCredits} tín chỉ</strong><span>Giới hạn: {MIN_CREDITS}–{MAX_CREDITS} tín chỉ</span></div>{cartHasConflict && <Alert className="cart-alert" type="warning" showIcon message="Giỏ đang có lớp trùng lịch." description="Xóa lớp xung đột trước khi gửi toàn bộ đăng ký." />}{cartCreditsInvalid && <Alert className="cart-alert" type="warning" showIcon message={`Giỏ vượt quá ${MAX_CREDITS} tín chỉ tối đa.`} />}{cartCredits > 0 && cartCredits < MIN_CREDITS && <Alert className="cart-alert" type="warning" showIcon message={`Lưu ý: giỏ hiện dưới mức tối thiểu ${MIN_CREDITS} tín chỉ.`} />}{!cart.length ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Chưa có lớp trong giỏ" /> : <div className="cart-list">{cart.map((section) => <div className="cart-item" key={section.id}><div><strong>{section.sectionCode}</strong><span>{section.subject.name}</span><small>{scheduleLabel(section)}</small></div><div className="cart-item-actions"><Button type="primary" size="small" loading={registrationMutation.isPending && registrationMutation.variables === section.id} onClick={() => confirmRegistration(section)}>Đăng ký</Button><Button type="text" danger icon={<DeleteOutlined />} aria-label={`Xóa ${section.sectionCode} khỏi giỏ`} onClick={() => setCart((current) => current.filter((item) => item.id !== section.id))} /></div></div>)}</div>}<Button className="submit-cart-button" type="primary" block loading={batchSubmitting} disabled={!cart.length || cartHasConflict || cartCreditsInvalid || registrationMutation.isPending} onClick={() => void submitCart()}>Gửi toàn bộ đăng ký ({cart.length} lớp · {cartCredits} TC)</Button></Card></aside></div>}
    <Card className="registration-timetable" title="Thời khóa biểu dự kiến" extra={<span className="timetable-hint">Tiết 1–6: sáng · Tiết 7–12: chiều</span>}>{!timetableItems.length ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Thêm lớp vào giỏ để xem lịch dự kiến." /> : <div className="registration-timetable-scroll"><div className="registration-timetable-grid"><div className="registration-timetable-corner">Kíp / Tiết</div>{dayColumns.map((day) => <div className="registration-timetable-day" key={day}>{days[day]}</div>)}{Array.from({ length: 12 }, (_, index) => <div className={`registration-timetable-period ${index === 0 || index === 6 ? "period-break" : ""}`} key={index + 1} style={{ gridColumn: 1, gridRow: index + 2 }}>{index === 0 ? "Sáng · 1" : index === 6 ? "Chiều · 7" : index + 1}</div>)}{timetableItems.filter((item) => dayColumns.includes(item.section.dayOfWeek)).map(({ section, source, conflict }) => <article className={`registration-timetable-event ${source} ${conflict ? "conflict" : ""}`} key={`${source}-${section.id}`} style={{ gridColumn: dayColumns.indexOf(section.dayOfWeek) + 2, gridRow: `${section.startPeriod + 1} / span ${section.endPeriod - section.startPeriod + 1}` }}><strong>{section.sectionCode}</strong><span>{section.subject.name}</span><small>Tiết {section.startPeriod}–{section.endPeriod} · {section.room.roomCode}</small>{conflict && <em>Trùng lịch</em>}</article>)}</div></div>}<div className="timetable-legend"><span><i className="registered-dot" /> Đã đăng ký</span><span><i className="cart-dot" /> Đang chọn</span><span><i className="conflict-dot" /> Có xung đột</span></div></Card>
  </>;
}
