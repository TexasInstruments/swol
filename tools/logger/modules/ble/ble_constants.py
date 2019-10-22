import enum
from construct import *

HCI_COMMAND_COMPLETE_EVENT_CODE = 0x0e
HCI_LE_EVENT_CODE = 0x3e
HCI_VE_EVENT_CODE = 0xff


class LLEventIds(enum.Enum):
    LL_EVT_POST_PROCESS_RF = 0x0001
    LL_EVT_DIRECTED_ADV_FAILED = 0x0002
    LL_EVT_SLAVE_CONN_CREATED = 0x0004
    LL_EVT_MASTER_CONN_CREATED = 0x0008
    LL_EVT_MASTER_CONN_CANCELLED = 0x0010
    LL_EVT_EXT_SCAN_TIMEOUT = 0x0020
    LL_EVT_EXT_ADV_TIMEOUT = 0x0040
    LL_EVT_SLAVE_CONN_CREATED_BAD_PARAM = 0x0080
    LL_RESERVED2 = 0x0100
    LL_EVT_RESET_SYSTEM_HARD = 0x0200
    LL_EVT_RESET_SYSTEM_SOFT = 0x0400
    LL_RESERVED3 = 0x0800
    LL_EVT_ADDRESS_RESOLUTION_TIMEOUT = 0x1000
    LL_EVT_INIT_DONE = 0x2000
    LL_EVT_OUT_OF_MEMORY = 0x4000
    SYSTEM_MESSAGE = 0x8000


class GAPEventIds(enum.Enum):
    GAP_OSAL_TIMER_INITIATING_TIMEOUT_EVT = 0x0001
    GAP_END_ADVERTISING_EVT = 0x0002
    GAP_CHANGE_RESOLVABLE_PRIVATE_ADDR_EVT = 0x0004
    GAP_CONN_PARAM_TIMEOUT_EVT = 0x0008


class SMEventIds(enum.Enum):
    SM_TIMEOUT_EVT = 0x0001
    SM_PAIRING_STATE_EVT = 0x0002
    SM_PAIRING_SEND_RSP_EVT = 0x0004
    SM_P256_RETRY_EVT = 0x0008
    SM_DHKEY_RETRY_EVT = 0x0010


class OsalCbEventIds(enum.Enum):
    APTO_EXPIRATION = 1
    L2CAP_EXPIRATION = 2


class GapBondMgrEventIds(enum.Enum):
    GAP_BOND_SYNC_CC_EVT = 0x0001
    GAP_BOND_SAVE_RCA_EVT = 0x0002
    GAP_BOND_POP_PAIR_QUEUE_EVT = 0x0004
    GAP_BOND_IDLE_EVT = 0x0008
    GAP_BOND_SYNC_RL_EVT = 0x0010


class SMDataMsgs(enum.Enum):
    SMP_PAIRING_REQ = 1
    SMP_PAIRING_RSP = 2
    SMP_PAIRING_CONFIRM = 3
    SMP_PAIRING_RANDOM = 4
    SMP_PAIRING_FAILED = 5
    SMP_ENCRYPTION_INFORMATION = 6
    SMP_MASTER_IDENTIFICATION = 7
    SMP_IDENTITY_INFORMATION = 8
    SMP_IDENTITY_ADDR_INFORMATION = 9
    SMP_SIGNING_INFORMATION = 10
    SMP_SECURITY_REQUEST = 11
    SMP_PAIRING_PUBLIC_KEY = 12
    SMP_PAIRING_DHKEY_CHECK = 13
    SMP_PAIRING_KEYPRESS_NOTIFICATION = 14


class GAPMsgs(enum.Enum):
    GAP_DEVICE_INIT_DONE_EVENT = 0x00
    GAP_DEVICE_DISCOVERY_EVENT = 0x01
    GAP_ADV_DATA_UPDATE_DONE_EVENT = 0x02
    GAP_MAKE_DISCOVERABLE_DONE_EVENT = 0x03
    GAP_END_DISCOVERABLE_DONE_EVENT = 0x04
    GAP_LINK_ESTABLISHED_EVENT = 0x05
    GAP_LINK_TERMINATED_EVENT = 0x06
    GAP_LINK_PARAM_UPDATE_EVENT = 0x07
    GAP_RANDOM_ADDR_CHANGED_EVENT = 0x08
    GAP_SIGNATURE_UPDATED_EVENT = 0x09
    GAP_AUTHENTICATION_COMPLETE_EVENT = 0x0a
    GAP_PASSKEY_NEEDED_EVENT = 0x0b
    GAP_SLAVE_REQUESTED_SECURITY_EVENT = 0x0c
    GAP_DEVICE_INFO_EVENT = 0x0d
    GAP_BOND_COMPLETE_EVENT = 0x0e
    GAP_PAIRING_REQ_EVENT = 0x0f
    GAP_AUTHENTICATION_FAILURE_EVT = 0x10
    GAP_UPDATE_LINK_PARAM_REQ_EVENT = 0x11
    GAP_SCAN_SESSION_END_EVENT = 0x12
    GAP_ADV_REMOVE_SET_EVENT = 0x13
    GAP_CONNECTING_CANCELLED_EVENT = 0x15
    GAP_BOND_LOST_EVENT = 0x17


class HCIPacketType(enum.Enum):
    HCI_CMD_PACKET = 0x01
    HCI_ACL_DATA_PACKET = 0x02
    HCI_SCO_DATA_PACKET = 0x03
    HCI_EVENT_PACKET = 0x04
    HCI_EXTENDED_CMD_PACKET = 0x09


class HCIGAPMsgs(enum.Enum):
    HCI_DISCONNECTION_COMPLETE_EVENT_CODE = 0x05
    HCI_ENCRYPTION_CHANGE_EVENT_CODE = 0x08
    HCI_READ_REMOTE_INFO_COMPLETE_EVENT_CODE = 0x0c
    HCI_COMMAND_COMPLETE_EVENT_CODE = 0x0e
    HCI_COMMAND_STATUS_EVENT_CODE = 0x0f
    HCI_BLE_HARDWARE_ERROR_EVENT_CODE = 0x10
    HCI_NUM_OF_COMPLETED_PACKETS_EVENT_CODE = 0x13
    HCI_DATA_BUFFER_OVERFLOW_EVENT = 0x1a
    HCI_KEY_REFRESH_COMPLETE_EVENT_CODE = 0x30
    HCI_APTO_EXPIRED_EVENT_CODE = 0x57
    HCI_LE_EVENT_CODE = 0x3e
    HCI_VE_EVENT_CODE = 0xff


class HCIEventMsgs(enum.Enum):
    HCI_BLE_CONNECTION_COMPLETE_EVENT = 0x01
    HCI_BLE_ADV_REPORT_EVENT = 0x02
    HCI_BLE_CONN_UPDATE_COMPLETE_EVENT = 0x03
    HCI_BLE_READ_REMOTE_FEATURE_COMPLETE_EVENT = 0x04
    HCI_BLE_LTK_REQUESTED_EVENT = 0x05
    HCI_BLE_REMOTE_CONN_PARAM_REQUEST_EVENT = 0x06
    HCI_BLE_DATA_LENGTH_CHANGE_EVENT = 0x07
    HCI_BLE_READ_LOCAL_P256_PUBLIC_KEY_COMPLETE_EVENT = 0x08
    HCI_BLE_GENERATE_DHKEY_COMPLETE_EVENT = 0x09
    HCI_BLE_ENHANCED_CONNECTION_COMPLETE_EVENT = 0x0a
    HCI_BLE_DIRECT_ADVERTISING_REPORT_EVENT = 0x0b
    HCI_BLE_PHY_UPDATE_COMPLETE_EVENT = 0x0c
    HCI_BLE_EXTENDED_ADV_REPORT_EVENT = 0x0d
    HCI_BLE_PERIODIC_ADV_SYNCH_ESTABLISHED_EVENT = 0x0e
    HCI_BLE_PERIODIC_ADV_REPORT_EVENT = 0x0f
    HCI_BLE_PERIODIC_ADV_SYNCH_LOST_EVENT = 0x10
    HCI_BLE_SCAN_TIMEOUT_EVENT = 0x11
    HCI_BLE_ADV_SET_TERMINATED_EVENT = 0x12
    HCI_BLE_SCAN_REQUEST_RECEIVED_EVENT = 0x13
    HCI_BLE_CHANNEL_SELECTION_ALGORITHM_EVENT = 0x14
    HCI_BLE_SCAN_REQ_REPORT_EVENT = 0x80
    HCI_VE_EVENT_CODE = 0xff


class GATTDataMsgs(enum.Enum):
    ATT_ERROR_RSP = 0x1
    ATT_EXCHANGE_MTU_REQ = 0x2
    ATT_EXCHANGE_MTU_RSP = 0x3
    ATT_FIND_INFO_REQ = 0x4
    ATT_FIND_INFO_RSP = 0x5
    ATT_FIND_BY_TYPE_VALUE_REQ = 0x6
    ATT_FIND_BY_TYPE_VALUE_RSP = 0x7
    ATT_READ_BY_TYPE_REQ = 0x8
    ATT_READ_BY_TYPE_RSP = 0x9
    ATT_READ_REQ = 0xa
    ATT_READ_RSP = 0xb
    ATT_READ_BLOB_REQ = 0xc
    ATT_READ_BLOB_RSP = 0xd
    ATT_READ_MULTI_REQ = 0xe
    ATT_READ_MULTI_RSP = 0xf
    ATT_READ_BY_GRP_TYPE_REQ = 0x10
    ATT_READ_BY_GRP_TYPE_RSP = 0x11
    ATT_WRITE_REQ = 0x12
    ATT_WRITE_RSP = 0x13
    ATT_PREPARE_WRITE_REQ = 0x16
    ATT_PREPARE_WRITE_RSP = 0x17
    ATT_EXECUTE_WRITE_REQ = 0x18
    ATT_EXECUTE_WRITE_RSP = 0x19
    ATT_HANDLE_VALUE_NOTI = 0x1b
    ATT_HANDLE_VALUE_IND = 0x1d
    ATT_HANDLE_VALUE_CFM = 0x1e
    ATT_WRITE_CMD = 82
    ATT_SIGNED_WRITE_CMD = 210
    ATT_METHOD_NOT_FOUND = None


class HCICmdOpcodes(enum.Enum):
    HCI_DISCONNECT = 0x0406
    HCI_READ_REMOTE_VERSION_INFO = 0x041d
    HCI_SET_EVENT_MASK = 0x0c01
    HCI_RESET = 0x0c03
    HCI_READ_TRANSMIT_POWER = 0x0c2d
    HCI_SET_CONTROLLER_TO_HOST_FLOW_CONTROL = 0x0c31
    HCI_HOST_BUFFER_SIZE = 0x0c33
    HCI_HOST_NUM_COMPLETED_PACKETS = 0x0c35
    HCI_SET_EVENT_MASK_PAGE_2 = 0x0c63
    HCI_READ_AUTH_PAYLOAD_TIMEOUT = 0x0c7b
    HCI_WRITE_AUTH_PAYLOAD_TIMEOUT = 0x0c7c
    HCI_READ_LOCAL_VERSION_INFO = 0x1001
    HCI_READ_LOCAL_SUPPORTED_COMMANDS = 0x1002
    HCI_READ_LOCAL_SUPPORTED_FEATURES = 0x1003
    HCI_READ_BDADDR = 0x1009
    HCI_READ_RSSI = 0x1405
    HCI_LE_SET_EVENT_MASK = 0x2001
    HCI_LE_READ_BUFFER_SIZE = 0x2002
    HCI_LE_READ_LOCAL_SUPPORTED_FEATURES = 0x2003
    HCI_LE_SET_RANDOM_ADDR = 0x2005
    HCI_LE_SET_ADV_PARAM = 0x2006
    HCI_LE_READ_ADV_CHANNEL_TX_POWER = 0x2007
    HCI_LE_SET_ADV_DATA = 0x2008
    HCI_LE_SET_SCAN_RSP_DATA = 0x2009
    HCI_LE_SET_ADV_ENABLE = 0x200a
    HCI_LE_SET_SCAN_PARAM = 0x200b
    HCI_LE_SET_SCAN_ENABLE = 0x200c
    HCI_LE_CREATE_CONNECTION = 0x200d
    HCI_LE_CREATE_CONNECTION_CANCEL = 0x200e
    HCI_LE_READ_WHITE_LIST_SIZE = 0x200f
    HCI_LE_CLEAR_WHITE_LIST = 0x2010
    HCI_LE_ADD_WHITE_LIST = 0x2011
    HCI_LE_REMOVE_WHITE_LIST = 0x2012
    HCI_LE_CONNECTION_UPDATE = 0x2013
    HCI_LE_SET_HOST_CHANNEL_CLASSIFICATION = 0x2014
    HCI_LE_READ_CHANNEL_MAP = 0x2015
    HCI_LE_READ_REMOTE_USED_FEATURES = 0x2016
    HCI_LE_ENCRYPT = 0x2017
    HCI_LE_RAND = 0x2018
    HCI_LE_START_ENCRYPTION = 0x2019
    HCI_LE_LTK_REQ_REPLY = 0x201a
    HCI_LE_LTK_REQ_NEG_REPLY = 0x201b
    HCI_LE_READ_SUPPORTED_STATES = 0x201c
    HCI_LE_RECEIVER_TEST = 0x201d
    HCI_LE_TRANSMITTER_TEST = 0x201e
    HCI_LE_TEST_END = 0x201f
    HCI_LE_REMOTE_CONN_PARAM_REQ_REPLY = 0x2020
    HCI_LE_REMOTE_CONN_PARAM_REQ_NEG_REPLY = 0x2021
    HCI_LE_SET_DATA_LENGTH = 0x2022
    HCI_LE_READ_SUGGESTED_DEFAULT_DATA_LENGTH = 0x2023
    HCI_LE_WRITE_SUGGESTED_DEFAULT_DATA_LENGTH = 0x2024
    HCI_LE_READ_LOCAL_P256_PUBLIC_KEY = 0x2025
    HCI_LE_GENERATE_DHKEY = 0x2026
    HCI_LE_ADD_DEVICE_TO_RESOLVING_LIST = 0x2027
    HCI_LE_REMOVE_DEVICE_FROM_RESOLVING_LIST = 0x2028
    HCI_LE_CLEAR_RESOLVING_LIST = 0x2029
    HCI_LE_READ_RESOLVING_LIST_SIZE = 0x202a
    HCI_LE_READ_PEER_RESOLVABLE_ADDRESS = 0x202b
    HCI_LE_READ_LOCAL_RESOLVABLE_ADDRESS = 0x202c
    HCI_LE_SET_ADDRESS_RESOLUTION_ENABLE = 0x202d
    HCI_LE_SET_RESOLVABLE_PRIVATE_ADDRESS_TIMEOUT = 0x202e
    HCI_LE_READ_MAX_DATA_LENGTH = 0x202f
    HCI_LE_SET_PRIVACY_MODE = 0x204e
    HCI_LE_READ_PHY = 0x2030
    HCI_LE_SET_DEFAULT_PHY = 0x2031
    HCI_LE_SET_PHY = 0x2032
    HCI_LE_ENHANCED_RECEIVER_TEST = 0x2033
    HCI_LE_ENHANCED_TRANSMITTER_TEST = 0x2034
    HCI_LE_READ_TX_POWER = 0x204b
    HCI_LE_READ_RF_PATH_COMPENSATION = 0x204c
    HCI_LE_WRITE_RF_PATH_COMPENSATION = 0x204d
    HCI_LE_SET_ADV_SET_RANDOM_ADDRESS = 0x2035
    HCI_LE_SET_EXT_ADV_PARAMETERS = 0x2036
    HCI_LE_SET_EXT_ADV_DATA = 0x2037
    HCI_LE_SET_EXT_SCAN_RESPONSE_DATA = 0x2038
    HCI_LE_SET_EXT_ADV_ENABLE = 0x2039
    HCI_LE_READ_MAX_ADV_DATA_LENGTH = 0x203a
    HCI_LE_READ_NUM_SUPPORTED_ADV_SETS = 0x203b
    HCI_LE_REMOVE_ADV_SET = 0x203c
    HCI_LE_CLEAR_ADV_SETS = 0x203d
    HCI_LE_SET_PERIODIC_ADV_PARAMETERS = 0x203e
    HCI_LE_SET_PERIODIC_ADV_DATA = 0x203f
    HCI_LE_SET_PERIODIC_ADV_ENABLE = 0x2040
    HCI_LE_SET_EXT_SCAN_PARAMETERS = 0x2041
    HCI_LE_SET_EXT_SCAN_ENABLE = 0x2042
    HCI_LE_EXT_CREATE_CONN = 0x2043
    HCI_EXT_SET_RX_GAIN = 0xfc00
    HCI_EXT_SET_TX_POWER = 0xfc01
    HCI_EXT_ONE_PKT_PER_EVT = 0xfc02
    HCI_EXT_CLK_DIVIDE_ON_HALT = 0xfc03
    HCI_EXT_DECLARE_NV_USAGE = 0xfc04
    HCI_EXT_DECRYPT = 0xfc05
    HCI_EXT_SET_LOCAL_SUPPORTED_FEATURES = 0xfc06
    HCI_EXT_SET_FAST_TX_RESP_TIME = 0xfc07
    HCI_EXT_MODEM_TEST_TX = 0xfc08
    HCI_EXT_MODEM_HOP_TEST_TX = 0xfc09
    HCI_EXT_MODEM_TEST_RX = 0xfc0a
    HCI_EXT_END_MODEM_TEST = 0xfc0b
    HCI_EXT_SET_BDADDR = 0xfc0c
    HCI_EXT_SET_SCA = 0xfc0d
    HCI_EXT_ENABLE_PTM = 0xfc0e
    HCI_EXT_SET_FREQ_TUNE = 0xfc0f
    HCI_EXT_SAVE_FREQ_TUNE = 0xfc10
    HCI_EXT_SET_MAX_DTM_TX_POWER = 0xfc11
    HCI_EXT_MAP_PM_IO_PORT = 0xfc12
    HCI_EXT_DISCONNECT_IMMED = 0xfc13
    HCI_EXT_PER = 0xfc14
    HCI_EXT_PER_BY_CHAN = 0xfc15
    HCI_EXT_EXTEND_RF_RANGE = 0xfc16
    HCI_EXT_HALT_DURING_RF = 0xfc19
    HCI_EXT_OVERRIDE_SL = 0xfc1a
    HCI_EXT_BUILD_REVISION = 0xfc1b
    HCI_EXT_DELAY_SLEEP = 0xfc1c
    HCI_EXT_RESET_SYSTEM = 0xfc1d
    HCI_EXT_OVERLAPPED_PROCESSING = 0xfc1e
    HCI_EXT_NUM_COMPLETED_PKTS_LIMIT = 0xfc1f
    HCI_EXT_GET_CONNECTION_INFO = 0xfc20
    HCI_EXT_SET_MAX_DATA_LENGTH = 0xfc21
    HCI_EXT_SET_DTM_TX_PKT_CNT = 0xfc24
    HCI_EXT_READ_RAND_ADDR = 0xfc25
    HCI_EXT_ENHANCED_MODEM_TEST_TX = 0xfc27
    HCI_EXT_ENHANCED_MODEM_HOP_TEST_TX = 0xfc28
    HCI_EXT_ENHANCED_MODEM_TEST_RX = 0xfc29
    HCI_EXT_LL_TEST_MODE = 0xfc70
    HCI_EXT_LE_SET_EXT_ADV_DATA = 0xfc71
    HCI_EXT_LE_SET_EXT_SCAN_RESPONSE_DATA = 0xfc72


class HCIEventOpcodes(enum.Enum):
    HCI_BLE_CONNECTION_COMPLETE_EVENT = 0x01
    HCI_BLE_ADV_REPORT_EVENT = 0x02
    HCI_BLE_CONN_UPDATE_COMPLETE_EVENT = 0x03
    HCI_BLE_READ_REMOTE_FEATURE_COMPLETE_EVENT = 0x04
    HCI_BLE_LTK_REQUESTED_EVENT = 0x05
    HCI_BLE_REMOTE_CONN_PARAM_REQUEST_EVENT = 0x06
    HCI_BLE_DATA_LENGTH_CHANGE_EVENT = 0x07
    HCI_BLE_READ_LOCAL_P256_PUBLIC_KEY_COMPLETE_EVENT = 0x08
    HCI_BLE_GENERATE_DHKEY_COMPLETE_EVENT = 0x09
    HCI_BLE_ENHANCED_CONNECTION_COMPLETE_EVENT = 0x0a
    HCI_BLE_DIRECT_ADVERTISING_REPORT_EVENT = 0x0b
    HCI_BLE_PHY_UPDATE_COMPLETE_EVENT = 0x0c
    HCI_BLE_EXTENDED_ADV_REPORT_EVENT = 0x0d
    HCI_BLE_PERIODIC_ADV_SYNCH_ESTABLISHED_EVENT = 0x0e
    HCI_BLE_PERIODIC_ADV_REPORT_EVENT = 0x0f
    HCI_BLE_PERIODIC_ADV_SYNCH_LOST_EVENT = 0x10
    HCI_BLE_SCAN_TIMEOUT_EVENT = 0x11
    HCI_BLE_ADV_SET_TERMINATED_EVENT = 0x12
    HCI_BLE_SCAN_REQUEST_RECEIVED_EVENT = 0x13
    HCI_BLE_CHANNEL_SELECTION_ALGORITHM_EVENT = 0x14
    HCI_BLE_SCAN_REQ_REPORT_EVENT = 0x80
    HCI_VE_EVENT_CODE = 0xff


class OSALMsgs(enum.Enum):
    LL_RF_MSG = 0
    CTRL_TO_HOST_EVT = 1
    HOST_TO_CTRL_CMD = 2
    HOST_TO_CTRL_DATA = 3
    HCI_DISCONENCT_COMPLETE_EVT = 5
    HCI_CMD_STAT = 16
    HCI_DATA_EVT_MSG = 144
    GAP_EVT_EVT_MSG = 145
    SM_EVT_EVT_MSG = 146
    HCI_EVT_MSG = 148
    L2CAP_DATA_IN_MSG = 160
    L2CAP_DATA_OUT_MSG = 161
    GATT_DATA_MSG = 176
    INCOMING_GATT_SERV_APP_MSG = 177
    INCOMING_SIGNAL_MSG = 178
    GAP_OSAL_MSG = 208


class LLTaskIds(enum.Enum):
    ADVERTISER = 1
    SCANNER = 2
    INITIATOR = 4
    SLAVE = 64
    MASTER = 128
    NONE = 0xFF


class LLTaskTypes(enum.Enum):
    LL_SCHED_START_IMMED = 0
    LL_SCHED_START_EVENT = 1
    LL_SCHED_START_PRIMARY = 2


LLTaskTypeToString = {
    LLTaskTypes.LL_SCHED_START_IMMED: "Starts immediately",
    LLTaskTypes.LL_SCHED_START_EVENT: "Starts at its T2E1 time",
    LLTaskTypes.LL_SCHED_START_PRIMARY: "Start primary task instead"
}


class LLSchedEvtTypes(enum.Enum):
    POST_RF = 0
    SCHED_NEXT = 1
    FIND_NEXT_SEC_TASK = 2
    FIND_START_TYPE = 3
    CONTROL_PROCE = 4
    RF_CB_EVENT = 5
    RF_STATE_EVENT = 6
    RF_OP_DONE_EVENT = 7


class RfEvents(enum.Enum):
    CmdDone = (1 << 0)
    LastCmdDone = (1 << 1)
    FGCmdDone = (1 << 2)
    LastFGCmdDone = (1 << 3)
    TxDone = (1 << 4)
    TXAck = (1 << 5)
    TxCtrl = (1 << 6)
    TxCtrlAck = (1 << 7)
    TxCtrlAckAck = (1 << 8)
    TxRetrans = (1 << 9)
    TxEntryDone = (1 << 10)
    TxBufferChange = (1 << 11)
    PaChanged = (1 << 14)
    RxOk = (1 << 16)
    RxNOk = (1 << 17)
    RxIgnored = (1 << 18)
    RxEmpty = (1 << 19)
    RxCtrl = (1 << 20)
    RxCtrlAck = (1 << 21)
    RxBufFull = (1 << 22)
    RxEntryDone = (1 << 23)
    DataWritten = (1 << 24)
    NDataWritten = (1 << 25)
    RxAborted = (1 << 26)
    RxCollisionDetected = (1 << 27)
    ModulesUnlocked = (1 << 29)
    InternalError = (1 << 31)
    MdmSoft = 0x0000002000000000
    RF_EventCmdCancelled = 0x1000000000000000
    RF_EventCmdAborted = 0x2000000000000000
    RF_EventCmdStopped = 0x4000000000000000
    RF_EventRatCh = 0x0800000000000000
    RF_EventPowerUp = 0x0400000000000000
    RF_EventError = 0x0200000000000000
    RF_EventCmdPreempted = 0x0100000000000000

class RfStates(enum.Enum):
    RF_FsmEventLastCommandDone = (1 << 1)
    RF_FsmEventWakeup = (1 << 2)
    RF_FsmEventPowerDown = (1 << 3)
    RF_FsmEventInitChangePhy = (1 << 10)
    RF_FsmEventFinishChangePhy = (1 << 11)
    RF_FsmEventCpeInt = (1 << 14)
    RF_FsmEventPowerStep = (1 << 29)
    RF_FsmEventRunScheduler = (1 << 30)

class VariableBytesToHex(Adapter):
    def _decode(self, obj, context, path):
        x = 0
        for key, val in enumerate(obj): x += val << (8 * key)
        return hex(x)


handle128BitUuid = Struct(
    "handle" / Int16ul,
    "UUID" / Hex(BytesInteger(16, swapped=True))
)

handle16BitUuid = Struct(
    "handle" / Int16ul,
    "UUID" / Hex(BytesInteger(2, swapped=True))
)

handleInformation = Struct(
    "found attribute handle" / Int16ul,
    "group end handle" / Int16ul
)

handleValue = Struct(
    "handle" / Int16ul,
    "value" / Hex(BytesInteger(this._.length - 2, swapped=True))
)

handleHandleValue = Struct(
    "attribute handle" / Int16ul,
    "group end handle" / Int16ul,
    "attribute value" / Hex(BytesInteger(this._.length - 4, swapped=True))
)

att_payload_parsing = {
    GATTDataMsgs.ATT_ERROR_RSP: Struct(
        "opcode in error" / Hex(Int8ul),
        "attribute handle" / Int16ul,
        "error code" / Hex(Int8ul),
    ),
    GATTDataMsgs.ATT_EXCHANGE_MTU_REQ: Struct(
        "MTU" / Int16ul
    ),
    GATTDataMsgs.ATT_EXCHANGE_MTU_RSP: Struct(
        "MTU" / Int16ul
    ),
    GATTDataMsgs.ATT_FIND_INFO_REQ: Struct(
        "starting handle" / Int16ul,
        "ending handle" / Int16ul
    ),
    GATTDataMsgs.ATT_FIND_INFO_RSP: Struct(
        "format" / Int8ul,
        "handle-UUID pair" / IfThenElse(this.format == 1,
                                        GreedyRange(handle16BitUuid),
                                        GreedyRange(handle128BitUuid))
    ),
    GATTDataMsgs.ATT_FIND_BY_TYPE_VALUE_REQ: Struct(
        "starting handle" / Int16ul,
        "ending handle" / Int16ul,
        "attribute type" / Hex(Int16ul),
        "attribute value" / Hex(GreedyBytes)
    ),
    GATTDataMsgs.ATT_FIND_BY_TYPE_VALUE_RSP: Struct(
        "handle info list" / GreedyRange(handleInformation)
    ),
    GATTDataMsgs.ATT_READ_BY_TYPE_REQ: Struct(
        "starting handle" / Int16ul,
        "ending handle" / Int16ul,
        "UUID" / VariableBytesToHex(GreedyBytes)
    ),
    GATTDataMsgs.ATT_READ_BY_TYPE_RSP: Struct(
        "length" / Hex(Int8ul),
        "handle-value-pairs" / GreedyRange(handleValue)
    ),
    GATTDataMsgs.ATT_READ_REQ: Struct(
        "attribute handle" / Int16ul
    ),
    GATTDataMsgs.ATT_READ_RSP: Struct(
        "attribute value" / Hex(GreedyBytes)
    ),
    GATTDataMsgs.ATT_READ_BLOB_REQ: Struct(
        "attribute handle" / Int16ul,
        "value offset" / Int16ul
    ),
    GATTDataMsgs.ATT_READ_BLOB_RSP: Struct(
        "part attribute value" / Hex(GreedyBytes)
    ),
    GATTDataMsgs.ATT_READ_MULTI_REQ: Struct(
        "set of handles" / GreedyRange(Int16ul)
    ),
    GATTDataMsgs.ATT_READ_MULTI_RSP: Struct(
        "set of values" / Hex(GreedyBytes)
    ),
    GATTDataMsgs.ATT_READ_BY_GRP_TYPE_REQ: Struct(
        "starting handle" / Int16ul,
        "ending handle" / Int16ul,
        "UUID" / VariableBytesToHex(GreedyBytes)
    ),
    GATTDataMsgs.ATT_READ_BY_GRP_TYPE_RSP: Struct(
        "length" / Int8ul,
        "attribute data list" / GreedyRange(handleHandleValue)
    ),
    GATTDataMsgs.ATT_WRITE_REQ: Struct(
        "attribute handle" / Int16ul,
        "attribute value" / Hex(GreedyBytes)
    ),
    GATTDataMsgs.ATT_WRITE_CMD: Struct(
        "attribute handle" / Int16ul,
        "attribute value" / Hex(GreedyBytes)
    ),
    GATTDataMsgs.ATT_SIGNED_WRITE_CMD: Struct(
        "attribute handle" / Int16ul,
        "attribute value" / Hex(GreedyBytes),
        "authentication signature" / Pointer(-12, Hex(Bytes(12)))
    ),
    GATTDataMsgs.ATT_PREPARE_WRITE_REQ: Struct(
        "attribute handle" / Int16ul,
        "value offset" / Int16ul,
        "attribute value" / Hex(GreedyBytes)
    ),
    GATTDataMsgs.ATT_PREPARE_WRITE_RSP: Struct(
        "attribute handle" / Int16ul,
        "value offset" / Int16ul,
        "attribute value" / Hex(GreedyBytes)
    ),
    GATTDataMsgs.ATT_EXECUTE_WRITE_REQ: Struct(
        "flags" / Hex(Int8ul)
    ),
    GATTDataMsgs.ATT_HANDLE_VALUE_NOTI: Struct(
        "attribute handle" / Int16ul,
        "attribute value" / Hex(GreedyBytes)
    ),
    GATTDataMsgs.ATT_HANDLE_VALUE_IND: Struct(
        "attribute handle" / Int16ul,
        "attribute value" / Hex(GreedyBytes)
    )
}

sm_payload_parsing = {
    SMDataMsgs.SMP_PAIRING_REQ: Struct(
        "I/O Capability" / Hex(Int8ul),
        "OOB data flag" / Hex(Int8ul),
        "Auth Req" / Hex(Int8ul),
        "Max Encryption Key Size" / Hex(Int8ul),
        "Initiator Key Distribution" / Hex(Int8ul),
        "Responder Key Distribution" / Hex(Int8ul)
    ),
    SMDataMsgs.SMP_PAIRING_RSP: Struct(
        "I/O Capability" / Hex(Int8ul),
        "OOB data flag" / Hex(Int8ul),
        "Auth Req" / Hex(Int8ul),
        "Max Encryption Key Size" / Hex(Int8ul),
        "Initiator Key Distribution" / Hex(Int8ul),
        "Responder Key Distribution" / Hex(Int8ul)
    ),
    SMDataMsgs.SMP_PAIRING_CONFIRM: Struct(
        "Confirm Value" / Hex(BytesInteger(16))
    ),
    SMDataMsgs.SMP_PAIRING_RANDOM: Struct(
        "Random Value" / Hex(BytesInteger(16))
    ),
    SMDataMsgs.SMP_PAIRING_FAILED: Struct(
        "Reason" / Hex(Int8ul)
    ),
    SMDataMsgs.SMP_ENCRYPTION_INFORMATION: Struct(
        "LTK" / Hex(BytesInteger(16))
    ),
    SMDataMsgs.SMP_MASTER_IDENTIFICATION: Struct(
        "EDIV" / Int16ul,
        "LTK" / Hex(BytesInteger(8))
    ),
    SMDataMsgs.SMP_IDENTITY_INFORMATION: Struct(
        "IRK" / Hex(BytesInteger(16))
    ),
    SMDataMsgs.SMP_IDENTITY_ADDR_INFORMATION: Struct(
        "Address Type" / Int8ul,
        "Address" / Hex(BytesInteger(6))
    ),
    SMDataMsgs.SMP_SIGNING_INFORMATION: Struct(
        "SRK" / Hex(BytesInteger(16))
    ),
    SMDataMsgs.SMP_SECURITY_REQUEST: Struct(
        "AuthReq" / Hex(Int8ul)
    ),
    SMDataMsgs.SMP_PAIRING_PUBLIC_KEY: Struct(
        "Public Key X" / Hex(BytesInteger(32)),
        "Public Key Y" / Hex(BytesInteger(32))
    ),
    SMDataMsgs.SMP_PAIRING_DHKEY_CHECK: Struct(
        "DHKey Check Value" / Hex(BytesInteger(16))
    ),
    SMDataMsgs.SMP_PAIRING_KEYPRESS_NOTIFICATION: Struct(
        "Notification Type" / Hex(Int8ul)
    ),
}


class Statuses(enum.Enum):
    SUCCESS = 0
    ERROR = None
