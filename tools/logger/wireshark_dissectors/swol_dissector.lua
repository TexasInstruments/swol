local proto_name = "wLogger"
local proto_description = "wLogger Protocol"

local logger_protocol = Proto(proto_name,  proto_description)

-- General Proto Fields
local gen_stream_id         = ProtoField.new("Stream ID",       proto_name .. ".gen.stream_id",     ftypes.STRING)
local gen_message         = ProtoField.new("Message",       proto_name .. ".gen.message",       ftypes.STRING)

-- WLAN Proto Fields
local wlan_time         = ProtoField.new("Time",      proto_name .. ".wlan.time",       ftypes.STRING)
local wlan_level        = ProtoField.new("Level",       proto_name .. ".wlan.level",      ftypes.STRING)
local wlan_file_name      = ProtoField.new("File Name",     proto_name .. ".wlan.file_name",      ftypes.STRING)
local wlan_function       = ProtoField.new("Function",    proto_name .. ".wlan.function",       ftypes.STRING)

-- BLE
-- SWO specific
local ble_swo_rat_s   = ProtoField.new("Radio Time Secs",                proto_name .. ".ble.rat_s",                     ftypes.DOUBLE)
local ble_swo_rtc_s   = ProtoField.new("Real Time Clock",                proto_name .. ".ble.rtc_s",                     ftypes.DOUBLE)
local ble_swo_rat_t   = ProtoField.new("Radio Time Ticks",               proto_name .. ".ble.rat_t",                     ftypes.UINT32)
local ble_swo_opcode  = ProtoField.new("SWO opcode",                     proto_name .. ".ble.opcode",                    ftypes.STRING)
local ble_swo_module  = ProtoField.new("SWO module",                     proto_name .. ".ble.module",                    ftypes.STRING)
local ble_swo_level   = ProtoField.new("SWO level",                      proto_name .. ".ble.level",                     ftypes.STRING)
local ble_swo_file    = ProtoField.new("SWO file",                       proto_name .. ".ble.file",                      ftypes.STRING)
local ble_swo_line    = ProtoField.new("SWO line",                       proto_name .. ".ble.line",                      ftypes.STRING)
local ble_swo_info    = ProtoField.new("SWO info",                       proto_name .. ".ble.info",                      ftypes.STRING)
local ble_swo_event   = ProtoField.new("SWO event",                      proto_name .. ".ble.event",                     ftypes.STRING)
-- BLE framer
local ble_ble_opcode  = ProtoField.new("BLE OpCode",                     proto_name .. ".ble.ble_opcode",                ftypes.STRING)
local ble_ble_layer   = ProtoField.new("BLE Layer",                      proto_name .. ".ble.ble_layer",                 ftypes.STRING)
local ble_ble_event   = ProtoField.new("BLE Event",                      proto_name .. ".ble.ble_event",                 ftypes.STRING)
local ble_ble_handle  = ProtoField.new("BLE Conn/adv handle",            proto_name .. ".ble.ble_handle",                ftypes.STRING)
local ble_ble_status  = ProtoField.new("BLE Status",                     proto_name .. ".ble.ble_status",                ftypes.STRING)
local ble_ble_info    = ProtoField.new("BLE Info",                       proto_name .. ".ble.ble_info",                  ftypes.STRING)
local ble_ble_ll_task = ProtoField.new("BLE LL Task",                    proto_name .. ".ble.ble_ll_task",               ftypes.STRING)
-- RF framer
local ble_rf_opcode   = ProtoField.new("RF OpCode",                      proto_name .. ".ble.rf_opcode",                 ftypes.STRING)
-- Driver framer
local ble_driver_file = ProtoField.new("Driver",                         proto_name .. ".ble.driver_file",               ftypes.STRING)
local ble_driver_status = ProtoField.new("Driver status",                proto_name .. ".ble.driver_status",             ftypes.STRING)
local ble_driver_power_constraint = ProtoField.new("Power constraint",   proto_name .. ".ble.driver_power_constraint",   ftypes.STRING)
-- Kernel framer
local ble_tirtos_log_event = ProtoField.new("Log Event",                 proto_name .. ".ble.tirtos_log_event",          ftypes.STRING)
local ble_tirtos_log_file  = ProtoField.new("File",                      proto_name .. ".ble.tirtos_log_file",           ftypes.STRING)
local ble_tirtos_log_line  = ProtoField.new("Line",                      proto_name .. ".ble.tirtos_log_line",           ftypes.STRING)


logger_protocol.fields = {
  gen_stream_id,
  gen_message,

  wlan_time,
  wlan_level,
  wlan_file_name,
  wlan_function,

  ble_swo_rat_s,
  ble_swo_rat_t,
  ble_swo_rtc_s,
  ble_swo_opcode,
  ble_swo_module,
  ble_swo_level,
  ble_swo_file,
  ble_swo_line,
  ble_swo_info,
  ble_swo_event,
  ble_ble_opcode,
  ble_ble_layer,
  ble_ble_event,
  ble_ble_handle,
  ble_ble_status,
  ble_ble_info,
  ble_ble_ll_task,
  ble_rf_opcode,
  ble_driver_file,
  ble_driver_status,
  ble_driver_power_constraint,
  ble_tirtos_log_event,
  ble_tirtos_log_file,
  ble_tirtos_log_line,
}

local ROOT_TREE        = 0
local FIRST_LEVEL_TREE = 1

function logger_protocol.dissector(buffer, pinfo, tree)
    local offset = 0
  local level = 0
  local trees = {}

  local buff_len = buffer:reported_length_remaining()

  trees[level] = tree:add(logger_protocol, buffer(), "wLogger")

  while (offset < buff_len) do
    length = buffer(offset, 4):le_uint()
        offset = offset + 4
        local key = buffer(offset, length):string(ENC_UTF_8)
        offset = offset + length

    length = buffer(offset, 4):le_uint()
        offset = offset + 4
        local value = buffer(offset, length):string(ENC_UTF_8)
        offset = offset + length


    if key == "ADD_LEVEL" then
      trees[level + 1] = trees[level]:add(value)
      level = level + 1

    elseif key == "END_ADD_LEVEL" then
      level = level - 1

    else
      if key == "Stream ID" then
        pinfo.cols.protocol = value

      elseif key == "Message" then
        pinfo.cols.info = value

      else
      end

      local found = false

      for index, item in pairs(logger_protocol.fields) do

        local fieldString = tostring(item)
        local i, j = string.find(fieldString, ": .* " .. proto_name .. ".")

        local item_name = string.sub(fieldString, i + 2, j -  string.len(proto_name) - 2)

        if key:lower() == item_name:lower() then
          if level == FIRST_LEVEL_TREE then
            trees[level]:add(item, value)
            found = true
            break
          end
        end

      end

      if not found then
        trees[level]:add(key .. " :", value)
      end


    end

  end


end


local raw_ip = DissectorTable.get("wtap_encap")
raw_ip:add(7, logger_protocol)
