import { requestClient } from '#/api/request';

/**
 * 用户个人中心端点（`/user/profile`）。ID 均为雪花字符串。
 */
export namespace ProfileApi {
  /** 角色精简信息 */
  export interface RoleSimpleRespVO {
    id: string;
    name: string;
  }

  /** 部门精简信息 */
  export interface DeptSimpleRespVO {
    id: string;
    name: string;
    parentId: string;
  }

  /** 岗位精简信息 */
  export interface PostSimpleRespVO {
    id: string;
    name: string;
  }

  /** 个人信息 RespVO */
  export interface UserProfileRespVO {
    address?: string;
    aiPreference?: Record<string, unknown>;
    avatar?: string;
    bio?: string;
    communicationStyle?: string;
    createTime: string;
    dept?: DeptSimpleRespVO;
    email?: string;
    expertise?: string;
    id: string;
    loginDate: string;
    loginIp: string;
    mobile?: string;
    nickname: string;
    posts?: PostSimpleRespVO[];
    roles?: RoleSimpleRespVO[];
    sex?: number;
    skills?: string[];
    tags?: string[];
    username: string;
    workScope?: string;
  }

  /** 修改个人信息 ReqVO（全部可选，服务端按提供字段更新） */
  export interface UserProfileUpdateReqVO {
    address?: string;
    aiPreference?: Record<string, unknown>;
    avatar?: string;
    bio?: string;
    communicationStyle?: 'casual' | 'formal' | 'technical';
    email?: string;
    expertise?: string;
    mobile?: string;
    nickname?: string;
    sex?: number;
    skills?: string[];
    tags?: string[];
    workScope?: string;
  }

  /** 修改密码 ReqVO（4-16 位） */
  export interface UserProfileUpdatePasswordReqVO {
    newPassword: string;
    oldPassword: string;
  }

  /** 在线设备信息 */
  export interface ProfileOnlineDeviceVO {
    browser?: string;
    deviceName?: string;
    ipAddress?: string;
    isCurrent: boolean;
    loginLocation?: string;
    loginTime?: string;
    online: boolean;
    os?: string;
    tokenId: string;
  }
}

/** 获得登录用户信息 */
export async function getUserProfile() {
  return requestClient.get<ProfileApi.UserProfileRespVO>(
    '/system/user/profile/get',
  );
}

/** 修改用户个人信息 */
export async function updateUserProfile(
  data: ProfileApi.UserProfileUpdateReqVO,
) {
  return requestClient.put('/system/user/profile/update', data);
}

/** 修改用户个人密码 */
export async function updateUserProfilePassword(
  data: ProfileApi.UserProfileUpdatePasswordReqVO,
) {
  return requestClient.put('/system/user/profile/update-password', data);
}

/** 获取我的在线设备列表 */
export async function getUserOnlineDevices() {
  return requestClient.get<ProfileApi.ProfileOnlineDeviceVO[]>(
    '/system/user/profile/online-devices',
  );
}

/** 踢出在线设备（tokenId 为路径参数） */
export async function kickoutOnlineDevice(tokenId: string) {
  return requestClient.delete(
    `/system/user/profile/online-devices/${encodeURIComponent(tokenId)}`,
  );
}
