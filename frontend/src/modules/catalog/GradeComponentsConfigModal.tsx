import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, App, Button, Form, Input, InputNumber, Modal, Space, Spin } from "antd";
import type { Section, GradeComponentInput } from "../../shared/api/api-types";
import { fetchGradeComponents, updateGradeComponents } from "./academicRecordsApi";
import { readApiError } from "../../shared/api/client";

interface GradeComponentsConfigModalProps {
  section: Section;
  onClose: () => void;
}

interface GradeComponentsForm {
  items: GradeComponentInput[];
}

const defaultComponents: GradeComponentInput[] = [
  { name: "Chuyên cần", weightPercentage: 10, maxScore: 10 },
  { name: "Giữa kỳ", weightPercentage: 30, maxScore: 10 },
  { name: "Cuối kỳ", weightPercentage: 60, maxScore: 10 },
];

export default function GradeComponentsConfigModal({
  section,
  onClose,
}: GradeComponentsConfigModalProps) {
  const [form] = Form.useForm<GradeComponentsForm>();
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const componentsQuery = useQuery({
    queryKey: ["grade-components", section.id],
    queryFn: () => fetchGradeComponents(section.id),
  });

  useEffect(() => {
    if (!componentsQuery.data) return;
    form.setFieldsValue({
      items: componentsQuery.data.length
        ? componentsQuery.data.map(({ name, weightPercentage, maxScore }) => ({
            name,
            weightPercentage,
            maxScore,
          }))
        : defaultComponents,
    });
  }, [componentsQuery.data, form]);

  const saveMutation = useMutation({
    mutationFn: (values: GradeComponentsForm) =>
      updateGradeComponents(section.id, { items: values.items }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["gradebook", section.id] });
      message.success("Đã lưu cấu hình điểm cho lớp học phần.");
      onClose();
    },
  });

  const errorBody = readApiError(saveMutation.error);

  return (
    <Modal
      title={`Cấu hình điểm · ${section.sectionCode} · ${section.semester.semesterCode}`}
      open
      onCancel={onClose}
      onOk={() => form.submit()}
      okText="Lưu cấu hình"
      cancelText="Hủy"
      confirmLoading={saveMutation.isPending}
      destroyOnHidden
    >
      {componentsQuery.isLoading && <div className="feature-loading"><Spin /></div>}
      {componentsQuery.isError && (
        <Alert
          type="error"
          showIcon
          message="Không tải được cấu hình điểm."
          action={<Button size="small" onClick={() => void componentsQuery.refetch()}>Thử lại</Button>}
        />
      )}
      {errorBody && (
        <Alert
          type="error"
          showIcon
          message={
            errorBody.error === "GRADE_COMPONENTS_LOCKED"
              ? "Không thể đổi cấu trúc vì lớp đã có điểm."
              : errorBody.details.map((item) => item.message).filter(Boolean).join("; ") ||
                errorBody.message
          }
          style={{ marginBottom: 16 }}
        />
      )}
      {componentsQuery.data && (
        <Form<GradeComponentsForm>
          form={form}
          layout="vertical"
          onFinish={(values) => saveMutation.mutate(values)}
        >
          <Form.List name="items">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Space key={field.key} align="start" style={{ display: "flex" }}>
                    <Form.Item
                      name={[field.name, "name"]}
                      label="Tên cột điểm"
                      rules={[{ required: true, whitespace: true, message: "Nhập tên cột" }]}
                    >
                      <Input maxLength={80} />
                    </Form.Item>
                    <Form.Item
                      name={[field.name, "weightPercentage"]}
                      label="Trọng số (%)"
                      rules={[{ required: true, message: "Nhập trọng số" }]}
                    >
                      <InputNumber min={0.01} max={100} precision={2} />
                    </Form.Item>
                    <Form.Item
                      name={[field.name, "maxScore"]}
                      label="Điểm tối đa"
                      rules={[{ required: true, message: "Nhập điểm tối đa" }]}
                    >
                      <InputNumber min={0.01} max={100} precision={2} />
                    </Form.Item>
                    <Button danger onClick={() => remove(field.name)} style={{ marginTop: 30 }}>
                      Xóa
                    </Button>
                  </Space>
                ))}
                <Button onClick={() => add({ name: "", weightPercentage: 0, maxScore: 10 })}>
                  Thêm cột điểm
                </Button>
              </>
            )}
          </Form.List>
          <Form.Item noStyle shouldUpdate>
            {() => {
              const items = form.getFieldValue("items") ?? [];
              const total = items.reduce(
                (sum: number, item: GradeComponentInput) =>
                  sum + Number(item?.weightPercentage ?? 0),
                0,
              );
              return (
                <Alert
                  type={Math.abs(total - 100) < 0.001 ? "success" : "warning"}
                  showIcon
                  message={`Tổng trọng số: ${total.toFixed(2)}% (yêu cầu 100%)`}
                  description="Điểm thành phần được quy đổi theo điểm tối đa; điểm tổng kết làm tròn về 0,5 gần nhất."
                  style={{ marginTop: 16 }}
                />
              );
            }}
          </Form.Item>
        </Form>
      )}
    </Modal>
  );
}
