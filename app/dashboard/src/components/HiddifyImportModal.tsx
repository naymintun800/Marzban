import {
  Alert,
  AlertIcon,
  Box,
  Button,
  Checkbox,
  FormControl,
  FormErrorMessage,
  FormLabel,
  Grid,
  GridItem,
  HStack,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Progress,
  Spinner,
  Text,
  VStack,
  chakra,
  useToast,
} from "@chakra-ui/react";
import { ArrowUpTrayIcon } from "@heroicons/react/24/outline";
import { zodResolver } from "@hookform/resolvers/zod";
import { useDashboard } from "contexts/DashboardContext";
import { FC, useRef, useState, useEffect } from "react";
import { Controller, FormProvider, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";
import { fetch } from "service/http";
import { Icon } from "./Icon";
import { RadioGroup } from "./RadioGroup";

const HiddifyImportIcon = chakra(ArrowUpTrayIcon, {
  baseStyle: {
    w: 5,
    h: 5,
  },
});

interface HiddifyImportResponse {
  successful_imports: number;
  failed_imports: number;
  errors: string[];
}

// Form validation schema
const HiddifyImportSchema = z.object({
  file: z.instanceof(File, { message: "Please select a file" }).nullable(),
  set_unlimited_expire: z.boolean(),
  enable_smart_username_parsing: z.boolean(),
  selected_protocols: z.array(z.string()).min(1, "Please select at least one protocol"),
  inbounds: z.record(z.array(z.string())).optional(),
  // Add proxy settings for each protocol (similar to UserDialog)
  proxies: z
    .record(z.string(), z.record(z.string(), z.any()))
    .transform((ins) => {
      const deleteIfEmpty = (obj: any, key: string) => {
        if (obj && obj[key] === "") {
          delete obj[key];
        }
      };
      deleteIfEmpty(ins.vmess, "id");
      deleteIfEmpty(ins.vless, "id");
      deleteIfEmpty(ins.trojan, "password");
      deleteIfEmpty(ins.shadowsocks, "password");
      deleteIfEmpty(ins.shadowsocks, "method");
      return ins;
    })
    .optional(),
}).refine(data => data.file !== null, {
  message: "Please select a file",
  path: ["file"],
});

type FormType = z.infer<typeof HiddifyImportSchema>;

const getDefaultValues = (): FormType => ({
  file: null,
  set_unlimited_expire: false,
  enable_smart_username_parsing: true,
  selected_protocols: [],
  inbounds: {},
  proxies: {
    vless: { id: "", flow: "" },
    vmess: { id: "" },
    trojan: { password: "" },
    shadowsocks: { password: "", method: "chacha20-ietf-poly1305" },
  },
});

export const HiddifyImportModal: FC = () => {
  const { isImportingHiddifyUsers, onImportHiddifyUsers } = useDashboard();
  const { t } = useTranslation();
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] = useState<HiddifyImportResponse | null>(null);
  const [isDeletingImported, setIsDeletingImported] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [importedUsersCount, setImportedUsersCount] = useState<number>(0);

  const form = useForm<FormType>({
    resolver: zodResolver(HiddifyImportSchema),
    defaultValues: getDefaultValues(),
  });

  // Check for imported users when modal opens
  useEffect(() => {
    if (isImportingHiddifyUsers) {
      checkImportedUsers();
    }
  }, [isImportingHiddifyUsers]);

  const onClose = () => {
    onImportHiddifyUsers(false);
    setImportResult(null);
    setShowDeleteConfirm(false);
    form.reset(getDefaultValues());
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === "application/json") {
      form.setValue("file", file);
      setImportResult(null);
    } else {
      toast({
        title: t("hiddifyImport.invalidFile"),
        description: t("hiddifyImport.invalidFileDesc"),
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const checkImportedUsers = async () => {
    try {
      // Get all users and filter those with custom_uuid (imported from Hiddify)
      const response = await fetch("/users?limit=1000") as { users: any[], total: number };
      const importedUsers = response.users.filter(user => user.custom_uuid);
      setImportedUsersCount(importedUsers.length);
      return importedUsers.length;
    } catch (error) {
      console.error("Error checking imported users:", error);
      return 0;
    }
  };

  const handleDeleteImported = async () => {
    setIsDeletingImported(true);
    try {
      // Get all users and filter those with custom_uuid
      const response = await fetch("/users?limit=10000") as { users: any[], total: number };
      const importedUsers = response.users.filter(user => user.custom_uuid);
      const usernamesToDelete = importedUsers.map(user => user.username);

      if (usernamesToDelete.length === 0) {
        toast({
          title: t("hiddifyImport.noImportedUsers"),
          status: "info",
          duration: 3000,
          isClosable: true,
        });
        setShowDeleteConfirm(false);
        return;
      }

      // Use the bulk delete endpoint
      await fetch("/users", {
        method: "DELETE",
        body: JSON.stringify({ usernames: usernamesToDelete }),
        headers: {
          "Content-Type": "application/json",
        },
      });
      
      toast({
        title: t("hiddifyImport.deleteSuccess"),
        description: t("hiddifyImport.deleteSuccessDesc", { count: importedUsers.length }),
        status: "success",
        duration: 5000,
        isClosable: true,
      });
      
      // Refresh users list
      useDashboard.getState().refetchUsers();
      setShowDeleteConfirm(false);
      setImportedUsersCount(0);
      
    } catch (error) {
      console.error("Error deleting imported users:", error);
      toast({
        title: t("hiddifyImport.deleteError"),
        description: t("hiddifyImport.deleteErrorDesc"),
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsDeletingImported(false);
    }
  };

  const showDeleteDialog = async () => {
    const count = await checkImportedUsers();
    if (count > 0) {
      setShowDeleteConfirm(true);
    } else {
      toast({
        title: t("hiddifyImport.noImportedUsers"),
        description: t("hiddifyImport.noImportedUsersDesc"),
        status: "info",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleImport = async () => {
    if (!form.getValues("file")) {
      toast({
        title: t("hiddifyImport.noFileSelected"),
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    if (form.getValues("selected_protocols").length === 0) {
      toast({
        title: t("hiddifyImport.noProtocolsSelected"),
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsImporting(true);
    setImportResult(null);

    try {
      const formData = new FormData();
      const file = form.getValues("file");
      if (file) {
        formData.append("file", file);
      }

      // Apply the same transform logic as in the schema
      const rawProxies = form.getValues("proxies");
      const transformedProxies = { ...rawProxies };

      const deleteIfEmpty = (obj: any, key: string) => {
        if (obj && obj[key] === "") {
          delete obj[key];
        }
      };

      if (transformedProxies.vmess) deleteIfEmpty(transformedProxies.vmess, "id");
      if (transformedProxies.vless) deleteIfEmpty(transformedProxies.vless, "id");
      if (transformedProxies.trojan) deleteIfEmpty(transformedProxies.trojan, "password");
      if (transformedProxies.shadowsocks) {
        deleteIfEmpty(transformedProxies.shadowsocks, "password");
        deleteIfEmpty(transformedProxies.shadowsocks, "method");
      }

      formData.append("set_unlimited_expire", form.getValues("set_unlimited_expire").toString());
      formData.append("enable_smart_username_parsing", form.getValues("enable_smart_username_parsing").toString());
      formData.append("selected_protocols", JSON.stringify(form.getValues("selected_protocols")));
      formData.append("inbounds", JSON.stringify(form.getValues("inbounds")));
      formData.append("proxies", JSON.stringify(transformedProxies));

      const response = await fetch("/users/import/hiddify", {
        method: "POST",
        body: formData,
      }) as HiddifyImportResponse;

      setImportResult(response);

      if (response.successful_imports > 0) {
        toast({
          title: t("hiddifyImport.importSuccess"),
          description: t("hiddifyImport.importSuccessDesc", {
            successful: response.successful_imports,
            failed: response.failed_imports,
          }),
          status: "success",
          duration: 5000,
          isClosable: true,
        });
        
        // Refresh users list
        useDashboard.getState().refetchUsers();
      }

      if (response.failed_imports > 0 || response.errors.length > 0) {
        toast({
          title: t("hiddifyImport.importWarning"),
          description: t("hiddifyImport.importWarningDesc", {
            failed: response.failed_imports,
          }),
          status: "warning",
          duration: 5000,
          isClosable: true,
        });
      }
    } catch (error) {
      console.error("Hiddify import error:", error);
      toast({
        title: t("hiddifyImport.importError"),
        description: t("hiddifyImport.importErrorDesc"),
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <Modal isOpen={isImportingHiddifyUsers} onClose={onClose} size="2xl">
      <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
      <FormProvider {...form}>
        <ModalContent mx="3" maxH="90vh" overflowY="auto">
          <ModalHeader pt={6}>
            <HStack gap={2}>
              <Icon color="primary">
                <HiddifyImportIcon color="white" />
              </Icon>
              <Text fontWeight="semibold" fontSize="lg">
                {t("hiddifyImport.title")}
              </Text>
            </HStack>
          </ModalHeader>
          <ModalCloseButton mt={3} disabled={isImporting || isDeletingImported} />
          
          <ModalBody pb={4}>
            <Grid
              templateColumns={{
                base: "repeat(1, 1fr)",
                md: "repeat(2, 1fr)",
              }}
              gap={6}
            >
              <GridItem>
                <VStack spacing={4} align="stretch">
                  {/* File Upload */}
                  <FormControl>
                    <FormLabel>{t("hiddifyImport.selectFile")}</FormLabel>
                    <Box position="relative">
                      <Input
                        ref={fileInputRef}
                        type="file"
                        accept=".json"
                        onChange={handleFileChange}
                        disabled={isImporting}
                        size="md"
                        borderRadius="6px"
                        height="40px"
                        sx={{
                          "&::file-selector-button": {
                            bg: "primary.500",
                            color: "white",
                            border: "none",
                            borderRadius: "md",
                            px: 4,
                            py: 2,
                            mr: 3,
                            cursor: "pointer",
                            fontSize: "sm",
                            _hover: {
                              bg: "primary.600",
                            },
                          },
                        }}
                      />
                      {form.watch("file")?.name && (
                        <Text fontSize="sm" color="green.500" mt={2}>
                          {t("hiddifyImport.fileSelected", { filename: form.watch("file")?.name })}
                        </Text>
                      )}
                    </Box>
                  </FormControl>

                  {/* Configuration Options */}
                  <FormControl>
                    <Controller
                      control={form.control}
                      name="set_unlimited_expire"
                      render={({ field: { onChange, value } }) => (
                        <Checkbox
                          isChecked={value}
                          onChange={onChange}
                          disabled={isImporting}
                          size="sm"
                        >
                          <Text fontSize="sm">{t("hiddifyImport.unlimitedExpiration")}</Text>
                        </Checkbox>
                      )}
                    />
                    <Text fontSize="xs" color="gray.500" mt={1}>
                      {t("hiddifyImport.unlimitedExpirationDesc")}
                    </Text>
                  </FormControl>

                  <FormControl>
                    <Controller
                      control={form.control}
                      name="enable_smart_username_parsing"
                      render={({ field: { onChange, value } }) => (
                        <Checkbox
                          isChecked={value}
                          onChange={onChange}
                          disabled={isImporting}
                          size="sm"
                        >
                          <Text fontSize="sm">{t("hiddifyImport.smartUsernameParsing")}</Text>
                        </Checkbox>
                      )}
                    />
                    <Text fontSize="xs" color="gray.500" mt={1}>
                      {t("hiddifyImport.smartUsernameParsingDesc")}
                    </Text>
                  </FormControl>

                  {/* Import Progress */}
                  {isImporting && (
                    <Box w="full">
                      <Text fontSize="sm" mb={2}>{t("hiddifyImport.importing")}</Text>
                      <Progress size="sm" isIndeterminate colorScheme="primary" />
                    </Box>
                  )}

                  {/* Import Results */}
                  {importResult && (
                    <Alert status={importResult.successful_imports > 0 ? "success" : "warning"}>
                      <AlertIcon />
                      <VStack align="start" spacing={1} flex={1}>
                        <Text fontSize="sm" fontWeight="medium">
                          {t("hiddifyImport.importComplete")}
                        </Text>
                        <Text fontSize="xs">
                          {t("hiddifyImport.importStats", {
                            successful: importResult.successful_imports,
                            failed: importResult.failed_imports,
                          })}
                        </Text>
                        {importResult.errors.length > 0 && (
                          <Box maxH="100px" overflowY="auto" w="full">
                            {importResult.errors.map((error, index) => (
                              <Text key={index} fontSize="xs" color="red.500">
                                • {error}
                              </Text>
                            ))}
                          </Box>
                        )}
                      </VStack>
                    </Alert>
                  )}
                </VStack>
              </GridItem>

              <GridItem>
                {/* Protocol Selection */}
                <FormControl
                  isInvalid={!!form.formState.errors.selected_protocols?.message}
                >
                  <FormLabel>{t("hiddifyImport.protocolSelection")}</FormLabel>
                  <Box position="relative" zIndex={1}>
                    <Controller
                      control={form.control}
                      name="selected_protocols"
                      render={({ field }) => {
                        return (
                          <RadioGroup
                            list={[
                              {
                                title: "vmess",
                                description: t("userDialog.vmessDesc"),
                              },
                              {
                                title: "vless",
                                description: t("userDialog.vlessDesc"),
                              },
                              {
                                title: "trojan",
                                description: t("userDialog.trojanDesc"),
                              },
                              {
                                title: "shadowsocks",
                                description: t("userDialog.shadowsocksDesc"),
                              },
                            ]}
                            disabled={isImporting}
                            {...field}
                          />
                        );
                      }}
                    />
                  </Box>
                    <FormErrorMessage>
                      {form.formState.errors.selected_protocols?.message}
                    </FormErrorMessage>
                  </FormControl>
                </GridItem>
              </Grid>
            </ModalBody>

          <ModalFooter pt={4} pb={6}>
            <HStack spacing={3} w="full" flexDirection={{ base: "column", sm: "row" }}>
              <Button
                variant="outline"
                onClick={onClose}
                disabled={isImporting || isDeletingImported}
                size="sm"
                flex={1}
              >
                {importResult ? t("close") : t("cancel")}
              </Button>
              <Button
                variant="outline"
                colorScheme="red"
                onClick={showDeleteDialog}
                disabled={isImporting || isDeletingImported}
                leftIcon={isDeletingImported ? <Spinner size="xs" /> : undefined}
                size="sm"
                flex={1}
              >
                {t("hiddifyImport.deleteImported")}
              </Button>
              <Button
                colorScheme="primary"
                onClick={handleImport}
                disabled={!form.watch("file") || form.watch("selected_protocols").length === 0 || isImporting || isDeletingImported}
                leftIcon={isImporting ? <Spinner size="xs" /> : undefined}
                size="sm"
                flex={1}
              >
                {t("hiddifyImport.importUsers")}
              </Button>
            </HStack>
          </ModalFooter>
        </ModalContent>
      </FormProvider>

      {/* Delete Confirmation Dialog */}
      <Modal isOpen={showDeleteConfirm} onClose={() => setShowDeleteConfirm(false)} size="md">
        <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
        <ModalContent mx="3">
          <ModalHeader>
            <Text fontWeight="semibold" fontSize="lg" color="red.500">
              {t("hiddifyImport.deleteConfirmTitle")}
            </Text>
          </ModalHeader>
          <ModalCloseButton disabled={isDeletingImported} />
          
          <ModalBody>
            <VStack spacing={3} align="stretch">
              <Alert status="warning">
                <AlertIcon />
                <Text fontSize="sm">
                  {t("hiddifyImport.deleteConfirmMessage", { count: importedUsersCount })}
                </Text>
              </Alert>
              <Text fontSize="sm" color="gray.600" _dark={{ color: "gray.400" }}>
                {t("hiddifyImport.deleteConfirmDesc")}
              </Text>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <HStack spacing={3} w="full">
              <Button
                variant="outline"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeletingImported}
                flex={1}
                size="sm"
              >
                {t("cancel")}
              </Button>
              <Button
                colorScheme="red"
                onClick={handleDeleteImported}
                disabled={isDeletingImported}
                leftIcon={isDeletingImported ? <Spinner size="xs" /> : undefined}
                flex={1}
                size="sm"
              >
                {t("hiddifyImport.confirmDelete")}
              </Button>
            </HStack>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Modal>
  );
};
