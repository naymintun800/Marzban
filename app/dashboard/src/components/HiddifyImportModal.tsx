import {
  Alert,
  AlertIcon,
  Box,
  Button,
  Checkbox,
  FormControl,
  FormLabel,
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
import { useDashboard } from "contexts/DashboardContext";
import { FC, useRef, useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { fetch } from "service/http";
import { Icon } from "./Icon";

const HiddifyImportIcon = chakra(ArrowUpTrayIcon, {
  baseStyle: {
    w: 5,
    h: 5,
  },
});

interface HiddifyImportConfig {
  set_unlimited_expire: boolean;
  enable_smart_username_parsing: boolean;
  protocols: string[];
}

interface HiddifyImportResponse {
  successful_imports: number;
  failed_imports: number;
  errors: string[];
}

export const HiddifyImportModal: FC = () => {
  const { isImportingHiddifyUsers, onImportHiddifyUsers } = useDashboard();
  const { t } = useTranslation();
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [config, setConfig] = useState<HiddifyImportConfig>({
    set_unlimited_expire: false,
    enable_smart_username_parsing: true,
    protocols: [],
  });
  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] = useState<HiddifyImportResponse | null>(null);
  const [isDeletingImported, setIsDeletingImported] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [importedUsersCount, setImportedUsersCount] = useState<number>(0);

  // Check for imported users when modal opens
  useEffect(() => {
    if (isImportingHiddifyUsers) {
      checkImportedUsers();
    }
  }, [isImportingHiddifyUsers]);

  const onClose = () => {
    onImportHiddifyUsers(false);
    setSelectedFile(null);
    setImportResult(null);
    setConfig({
      set_unlimited_expire: false,
      enable_smart_username_parsing: true,
      protocols: [],
    });
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === "application/json") {
      setSelectedFile(file);
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

  const handleProtocolChange = (protocols: string[]) => {
    setConfig(prev => ({ ...prev, protocols }));
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
      const response = await fetch("/users?limit=1000") as { users: any[], total: number };
      const importedUsers = response.users.filter(user => user.custom_uuid);
      
      // Delete each imported user
      const deletePromises = importedUsers.map(user => 
        fetch(`/user/${user.username}`, { method: "DELETE" })
      );
      
      await Promise.all(deletePromises);
      
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
    if (!selectedFile) {
      toast({
        title: t("hiddifyImport.noFileSelected"),
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    if (config.protocols.length === 0) {
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
      formData.append("file", selectedFile);
      formData.append("set_unlimited_expire", config.set_unlimited_expire.toString());
      formData.append("enable_smart_username_parsing", config.enable_smart_username_parsing.toString());
      formData.append("protocols", JSON.stringify(config.protocols));

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
    <Modal isOpen={isImportingHiddifyUsers} onClose={onClose} size="lg">
      <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
      <ModalContent mx="3">
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
        <ModalCloseButton mt={3} disabled={isImporting} />
        
        <ModalBody>
          <VStack spacing={4} align="stretch">
            {/* File Upload */}
            <FormControl>
              <FormLabel>{t("hiddifyImport.selectFile")}</FormLabel>
              <Input
                ref={fileInputRef}
                type="file"
                accept=".json"
                onChange={handleFileChange}
                disabled={isImporting}
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
                    _hover: {
                      bg: "primary.600",
                    },
                  },
                }}
              />
              {selectedFile && (
                <Text fontSize="sm" color="green.500" mt={1}>
                  {t("hiddifyImport.fileSelected", { filename: selectedFile.name })}
                </Text>
              )}
            </FormControl>

            {/* Configuration Options */}
            <VStack spacing={3} align="stretch">
              <FormControl>
                <Checkbox
                  isChecked={config.set_unlimited_expire}
                  onChange={(e) => setConfig(prev => ({ ...prev, set_unlimited_expire: e.target.checked }))}
                  disabled={isImporting}
                >
                  <FormLabel m={0}>{t("hiddifyImport.unlimitedExpiration")}</FormLabel>
                </Checkbox>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  {t("hiddifyImport.unlimitedExpirationDesc")}
                </Text>
              </FormControl>

              <FormControl>
                <Checkbox
                  isChecked={config.enable_smart_username_parsing}
                  onChange={(e) => setConfig(prev => ({ ...prev, enable_smart_username_parsing: e.target.checked }))}
                  disabled={isImporting}
                >
                  <FormLabel m={0}>{t("hiddifyImport.smartUsernameParsing")}</FormLabel>
                </Checkbox>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  {t("hiddifyImport.smartUsernameParsingDesc")}
                </Text>
              </FormControl>

              {/* Protocol Selection */}
              <FormControl>
                <FormLabel>{t("hiddifyImport.protocolSelection")}</FormLabel>
                <VStack spacing={2} align="stretch">
                  {[
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
                  ].map((protocol) => (
                    <Box
                      key={protocol.title}
                      borderWidth="1px"
                      borderRadius="md"
                      p={3}
                      cursor="pointer"
                      borderColor={config.protocols.includes(protocol.title) ? "primary.500" : "gray.200"}
                      bg={config.protocols.includes(protocol.title) ? "primary.50" : "transparent"}
                      _dark={{
                        borderColor: config.protocols.includes(protocol.title) ? "primary.500" : "gray.600",
                        bg: config.protocols.includes(protocol.title) ? "primary.900" : "transparent",
                      }}
                      onClick={() => {
                        if (!isImporting) {
                          const newProtocols = config.protocols.includes(protocol.title)
                            ? config.protocols.filter(p => p !== protocol.title)
                            : [...config.protocols, protocol.title];
                          handleProtocolChange(newProtocols);
                        }
                      }}
                    >
                      <Checkbox
                        isChecked={config.protocols.includes(protocol.title)}
                        isDisabled={isImporting}
                        onChange={() => {}} // Handled by Box onClick
                        pointerEvents="none"
                      >
                        <VStack align="start" spacing={1} ml={2}>
                          <Text fontSize="sm" fontWeight="medium" textTransform="uppercase">
                            {protocol.title}
                          </Text>
                          <Text fontSize="xs" color="gray.600" _dark={{ color: "gray.400" }}>
                            {protocol.description}
                          </Text>
                        </VStack>
                      </Checkbox>
                    </Box>
                  ))}
                </VStack>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  {t("hiddifyImport.protocolSelectionDesc")}
                </Text>
              </FormControl>
            </VStack>

            {/* Import Progress */}
            {isImporting && (
              <Box>
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
        </ModalBody>

        <ModalFooter>
          <HStack spacing={3} w="full">
            <Button
              variant="outline"
              onClick={onClose}
              disabled={isImporting || isDeletingImported}
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
              flex={1}
            >
              {t("hiddifyImport.deleteImported")}
            </Button>
            <Button
              colorScheme="primary"
              onClick={handleImport}
              disabled={!selectedFile || config.protocols.length === 0 || isImporting || isDeletingImported}
              leftIcon={isImporting ? <Spinner size="xs" /> : undefined}
              flex={1}
            >
              {t("hiddifyImport.importUsers")}
            </Button>
          </HStack>
        </ModalFooter>
      </ModalContent>

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
              >
                {t("cancel")}
              </Button>
              <Button
                colorScheme="red"
                onClick={handleDeleteImported}
                disabled={isDeletingImported}
                leftIcon={isDeletingImported ? <Spinner size="xs" /> : undefined}
                flex={1}
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